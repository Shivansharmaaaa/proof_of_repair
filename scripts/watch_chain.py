"""Live feed of Proof of Repair anchors on Ethereum, joined with the PostgreSQL records they cover.

Prints every MerkleRootAnchored event since the contract was deployed, then keeps polling,
so a new line appears as soon as an anchor is mined. Ctrl-C to stop.

Run: python scripts/watch_chain.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web3 import Web3  # noqa: E402

from src.blockchain.evm_ledger import Web3Ledger  # noqa: E402

EVENT_SIG = Web3.keccak(text="MerkleRootAnchored(bytes32,string,string,address,uint256)").hex()


def records_for_root(reg, root_hex: str) -> str:
    if reg is None:
        return ""
    with reg._connect() as conn:
        rows = conn.execute(
            """
            SELECT r.asset_type, r.asset_id, r.fault_code FROM anchor_batches b
            JOIN record_anchors ra ON ra.batch_id = b.batch_id
            JOIN repair_records r ON r.proof_id = ra.proof_id
            WHERE b.merkle_root = %s ORDER BY ra.leaf_index
            """,
            (root_hex,),
        ).fetchall()
    if not rows:
        return "not in this database"
    return "; ".join(f"{r['asset_type']} {r['asset_id']} {r['fault_code']}" for r in rows)


def main() -> None:
    cfg = os.environ.get("CHAIN_CONFIG") or (
        ROOT / "artifacts/chain_config.sepolia.json"
        if (ROOT / "artifacts/chain_config.sepolia.json").exists()
        else ROOT / "artifacts/chain_config.json"
    )
    ledger = Web3Ledger(cfg)
    w3, contract = ledger.w3, ledger.contract
    address = ledger.config["contract_address"]
    try:
        from src.cloud.pg_registry import PgRegistry

        reg = PgRegistry()
    except Exception:
        reg = None

    start = 0
    if ledger.config.get("deploy_tx"):
        start = w3.eth.get_transaction_receipt(ledger.config["deploy_tx"]).blockNumber
    explorer = ledger.config.get("explorer_tx_prefix") or ""
    print(f"Watching {ledger.network} (chainId {ledger.chain_id}) contract {address}")
    print(f"Explorer: {(ledger.config.get('explorer_address_prefix') or '') + address}\n")

    event = contract.events.MerkleRootAnchored()
    seen = set()
    next_block = start
    while True:
        try:
            latest = w3.eth.block_number
            if latest >= next_block:
                logs = w3.eth.get_logs({
                    "address": Web3.to_checksum_address(address),
                    "fromBlock": next_block,
                    "toBlock": latest,
                    "topics": [EVENT_SIG if EVENT_SIG.startswith("0x") else "0x" + EVENT_SIG],
                })
                for log in logs:
                    key = (log["transactionHash"].hex(), log["logIndex"])
                    if key in seen:
                        continue
                    seen.add(key)
                    ev = event.process_log(log)
                    root = ev.args.merkleRoot.hex().removeprefix("0x")
                    tx = log["transactionHash"].hex()
                    tx = tx if tx.startswith("0x") else "0x" + tx
                    when = datetime.fromtimestamp(ev.args.anchoredAt).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[block {log['blockNumber']}] {when}  batch {ev.args.batchId}")
                    print(f"   Merkle root  {root}")
                    print(f"   records      {records_for_root(reg, root)}")
                    print(f"   tx           {explorer}{tx}\n")
                next_block = latest + 1
            print(f"\r   … watching, latest block {latest} (anchor in the app to see a new line)", end="", flush=True)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\r   (RPC hiccup: {e.__class__.__name__}; retrying)", end="", flush=True)
        time.sleep(6)
        print("\r" + " " * 90 + "\r", end="")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
