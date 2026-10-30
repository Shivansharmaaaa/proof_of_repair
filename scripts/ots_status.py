"""Check OpenTimestamps receipts against the public calendars; record Bitcoin confirmations.

For each .ots receipt: ask the calendar that holds it whether the commitment is now in a Bitcoin
block; if so, merge that proof into the .ots file and mark the anchor batch "confirmed" in PostgreSQL.
Prints a mempool.space link for every confirmed Bitcoin block.

Run: python scripts/ots_status.py            (all receipts)
     python scripts/ots_status.py --db-only  (only receipts referenced by anchor_batches)
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
from opentimestamps.core.serialize import StreamDeserializationContext, StreamSerializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STORE = ROOT / "artifacts" / "ots_calendar"


def find_node(ts: Timestamp, msg: bytes):
    if ts.msg == msg:
        return ts
    for child in ts.ops.values():
        hit = find_node(child, msg)
        if hit is not None:
            return hit
    return None


def bitcoin_header_matches(height: int, merkle_root_le: bytes) -> bool:
    """Independent check: the proof's final hash equals the block's Merkle root on mempool.space."""
    import urllib.request

    base = "https://mempool.space/api"
    block_hash = urllib.request.urlopen(f"{base}/block-height/{height}", timeout=15).read().decode().strip()
    block = json.load(urllib.request.urlopen(f"{base}/block/{block_hash}", timeout=15))
    return block["merkle_root"] == merkle_root_le[::-1].hex()


def bitcoin_txids(path: Path) -> list[str]:
    """Bitcoin transactions (calendar OP_RETURN txs) that carry this receipt's commitment."""
    import hashlib

    from bitcoin.core import CTransaction

    with path.open("rb") as fh:
        ts = DetachedTimestampFile.deserialize(StreamDeserializationContext(fh)).timestamp
    found: set[str] = set()

    def walk(node: Timestamp) -> None:
        if len(node.msg) > 64:  # 32-byte hashes are skipped; a serialized transaction is longer
            try:
                CTransaction.deserialize(node.msg)
                found.add(hashlib.sha256(hashlib.sha256(node.msg).digest()).digest()[::-1].hex())
            except Exception:
                pass
        for child in node.ops.values():
            walk(child)

    walk(ts)
    return sorted(found)


def upgrade(path: Path) -> list[tuple[int, bytes]]:
    """Return (Bitcoin block height, attested merkle root) pairs for this receipt, after asking the calendars."""
    with path.open("rb") as fh:
        detached = DetachedTimestampFile.deserialize(StreamDeserializationContext(fh))
    ts = detached.timestamp
    changed = False
    for msg, att in list(ts.all_attestations()):
        if not isinstance(att, PendingAttestation):
            continue
        try:
            upgraded = RemoteCalendar(att.uri, user_agent="proof-of-repair/2.0").get_timestamp(msg, timeout=15)
        except Exception:
            continue  # not in a Bitcoin block yet, or calendar unreachable
        node = find_node(ts, msg)
        if node is not None:
            node.merge(upgraded)
            changed = True
    found = sorted({(a.height, m) for m, a in ts.all_attestations() if isinstance(a, BitcoinBlockHeaderAttestation)})
    if changed:
        buf = io.BytesIO()
        detached.serialize(StreamSerializationContext(buf))
        path.write_bytes(buf.getvalue())
    return found


def main() -> None:
    receipts = {p.stem: p for p in STORE.glob("*.ots")}
    batches = {}
    try:
        from src.cloud.pg_registry import PgRegistry

        reg = PgRegistry()
        with reg._connect() as conn:
            for row in conn.execute("SELECT batch_id, ots_receipt_id, merkle_root FROM anchor_batches"):
                batches[row["ots_receipt_id"]] = row
    except Exception as e:
        reg = None
        print(f"(database not reachable: {e}; checking files only)")
    if "--db-only" in sys.argv:
        receipts = {k: v for k, v in receipts.items() if k in batches}

    def created(item):
        meta_path = STORE / f"{item[0]}.json"
        return (meta_path if meta_path.exists() else item[1]).stat().st_mtime

    for rid, path in sorted(receipts.items(), key=created):
        meta_path = STORE / f"{rid}.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        when = datetime.fromtimestamp((meta_path if meta_path.exists() else path).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        attested = upgrade(path)
        heights = [h for h, _ in attested]
        batch = batches.get(rid)
        label = f"batch {batch['batch_id']}" if batch else "not in current DB"
        root = (batch["merkle_root"] if batch else (meta.get("receipt") or {}).get("digest_hex") or "")[:16]
        if heights:
            try:
                checked = "matches the Bitcoin block header (mempool.space)" if bitcoin_header_matches(*attested[0]) \
                    else "DOES NOT match the block header"
            except Exception as e:
                checked = f"block header check skipped ({e.__class__.__name__})"
            print(f"CONFIRMED  {when}  root {root}…  Bitcoin block {heights[0]}  ({label})")
            print(f"           proof {checked}")
            print(f"           block https://mempool.space/block/{heights[0]}")
            for txid in bitcoin_txids(path):
                print(f"           tx    https://mempool.space/tx/{txid}")
            if batch and reg:
                with reg._connect() as conn:
                    conn.execute(
                        "UPDATE anchor_batches SET ots_status = 'confirmed', "
                        "meta = coalesce(meta, '{}'::jsonb) || jsonb_build_object('bitcoin_block', %s::int) "
                        "WHERE batch_id = %s",
                        (heights[0], batch["batch_id"]),
                    )
        else:
            print(f"pending    {when}  root {root}…  waiting for a Bitcoin block ({label})")
        print(f"           receipt file: {path}")
    print("\nPublic check: drag a receipt file onto https://opentimestamps.org (Stamp & Verify).")


if __name__ == "__main__":
    main()
