"""Audit: is every PostgreSQL record backed by the blockchain, and vice versa?

For each anchor batch in the database:
  tx receipt exists, succeeded, went to our contract, block matches,
  the on-chain MerkleRootAnchored event carries the same root + batch id,
  and the contract says isRootAnchored(root) == true.
For each repair record:
  report hash and leaf digest recompute, its stored Merkle path reaches the batch root.

Run: python scripts/check_db_chain.py      (uses CHAIN_CONFIG, default: Sepolia config if present)
Exit code 0 = everything consistent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blockchain.evm_ledger import Web3Ledger  # noqa: E402
from src.cloud.pg_registry import PgRegistry  # noqa: E402
from src.por.proof import ProofOfRepair  # noqa: E402
from src.por.verify import verify_leaf_digest, verify_merkle_inclusion, verify_report_hash  # noqa: E402


def etherscan_transactions(ledger):
    """Contract transactions as Etherscan lists them (None if no API key or not a public network)."""
    import json
    import urllib.request

    from src.blockchain.evm_ledger import _env_value

    key = _env_value("ETHERSCAN_API_KEY")
    if not key or not ledger.config.get("explorer_tx_prefix"):
        return None
    url = (
        f"https://api.etherscan.io/v2/api?chainid={ledger.chain_id}&module=account&action=txlist"
        f"&address={ledger.config['contract_address']}&sort=asc&apikey={key}"
    )
    try:
        data = json.load(urllib.request.urlopen(url, timeout=20))
    except Exception as e:
        print(f"(Etherscan check skipped: {e.__class__.__name__})")
        return None
    return data.get("result") if isinstance(data.get("result"), list) else []


def main() -> int:
    cfg_path = os.environ.get("CHAIN_CONFIG") or (
        ROOT / "artifacts/chain_config.sepolia.json"
        if (ROOT / "artifacts/chain_config.sepolia.json").exists()
        else ROOT / "artifacts/chain_config.json"
    )
    ledger = Web3Ledger(cfg_path)
    reg = PgRegistry()
    w3, contract = ledger.w3, ledger.contract
    problems = 0

    def check(ok: bool, label: str) -> None:
        nonlocal problems
        problems += 0 if ok else 1
        print(f"   {'OK  ' if ok else 'FAIL'} {label}")

    print(f"Chain: {ledger.network} (chainId {ledger.chain_id}) contract {ledger.config['contract_address']}")
    print(f"DB:    {reg.url}\n")

    with reg._connect() as conn:
        batches = conn.execute("SELECT * FROM anchor_batches ORDER BY anchored_at").fetchall()
        records = conn.execute(
            """
            SELECT r.proof_id::text AS id, r.asset_type, r.asset_id, r.leaf_digest,
                   ra.batch_id, ra.merkle_proof, b.merkle_root
            FROM repair_records r
            LEFT JOIN record_anchors ra ON ra.proof_id = r.proof_id
            LEFT JOIN anchor_batches b ON b.batch_id = ra.batch_id
            ORDER BY r.sealed_at
            """
        ).fetchall()

    event = contract.events.MerkleRootAnchored()
    for b in batches:
        print(f"Batch {b['batch_id']}  root {b['merkle_root'][:16]}…  tx {str(b['chain_tx'])[:18]}…")
        check(b["chain_id"] == ledger.chain_id, f"stored chainId {b['chain_id']} matches the live chain")
        check((b["contract_address"] or "").lower() == ledger.config["contract_address"].lower(),
              "stored contract address matches the deployed contract")
        try:
            rcpt = w3.eth.get_transaction_receipt(b["chain_tx"])
        except Exception as e:
            check(False, f"transaction found on chain ({e.__class__.__name__})")
            continue
        check(rcpt.status == 1, "transaction succeeded (status 1)")
        check(rcpt["to"] and rcpt["to"].lower() == ledger.config["contract_address"].lower(), "sent to our contract")
        check(rcpt.blockNumber == b["block_number"], f"block {rcpt.blockNumber} matches DB block {b['block_number']}")
        logs = event.process_receipt(rcpt)
        on_chain = [(l.args.merkleRoot.hex().removeprefix("0x"), l.args.batchId) for l in logs]
        check((b["merkle_root"], b["batch_id"]) in on_chain, "event MerkleRootAnchored has the same root + batch id")
        check(contract.functions.isRootAnchored(bytes.fromhex(b["merkle_root"])).call(),
              "contract.isRootAnchored(root) == true")
        check(b["leaf_count"] == len((b["meta"] or {}).get("leaf_order", [])), f"{b['leaf_count']} leaves recorded")
        print()

    pending = 0
    for r in records:
        por = ProofOfRepair.from_dict(reg.get_proof(r["id"]))
        label = f"{r['asset_type']:<9} {r['asset_id']:<18}"
        if not r["batch_id"]:
            pending += 1
            print(f"Record {label} not anchored yet (pending batch)")
            continue
        print(f"Record {label} -> batch {r['batch_id']}")
        check(verify_report_hash(por), "report hash recomputes (report unchanged)")
        check(verify_leaf_digest(por), "leaf digest recomputes (device, usage, report, evidence unchanged)")
        mp = r["merkle_proof"] or {}
        check(bool(mp) and mp.get("root_hex") == r["merkle_root"], "stored Merkle path ends at the batch root")
        check(bool(mp) and verify_merkle_inclusion(mp, r["leaf_digest"]), "Merkle path proves the leaf is in that root")

    explorer_rows = etherscan_transactions(ledger)
    if explorer_rows is not None:
        print("\nEtherscan (public explorer) vs database")
        db_txs = {str(b["chain_tx"]).lower() for b in batches}
        ok_txs = {t["hash"].lower() for t in explorer_rows if t.get("isError") == "0" and t.get("to")}
        failed = [t["hash"] for t in explorer_rows if t.get("isError") == "1"]
        for b in batches:
            check(str(b["chain_tx"]).lower() in ok_txs, f"Etherscan lists {str(b['chain_tx'])[:18]}… (batch {b['batch_id']})")
        extra = ok_txs - db_txs
        check(not extra, "every successful anchor on Etherscan is in the database"
              + (f" (missing: {', '.join(t[:14] for t in extra)})" if extra else ""))
        if failed:
            print(f"   note {len(failed)} failed transaction(s) on chain (reverted, no data stored): "
                  + ", ".join(t[:14] + "…" for t in failed))

    print(f"\n{len(batches)} batch(es), {len(records)} record(s), {pending} pending, {problems} problem(s)")
    print("RESULT:", "DATABASE AND BLOCKCHAIN ARE CONSISTENT" if problems == 0 else "MISMATCH FOUND")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
