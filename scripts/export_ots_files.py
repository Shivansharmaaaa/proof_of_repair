"""Export file pairs for public verification on https://opentimestamps.org.

For every anchor batch, writes to artifacts/ots_public/:
  <date>_<batch>.bin       the exact bytes whose SHA-256 is the batch's Merkle root
  <date>_<batch>.bin.ots   the OpenTimestamps receipt for that root (Bitcoin proof once confirmed)
The server writes these after each anchor; run this to refresh them after scripts/ots_status.py
has pulled Bitcoin confirmations. Drag both onto opentimestamps.org -> Stamp & Verify.

Run: python scripts/export_ots_files.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blockchain.ots_export import export_batch  # noqa: E402

RECEIPTS = ROOT / "artifacts" / "ots_calendar"
OUT = ROOT / "artifacts" / "ots_public"


def batches():
    """(batch_id, merkle_root, receipt_id, leaves, when, proof_lookup) from PostgreSQL and the legacy SQLite registry."""
    try:
        from src.cloud.pg_registry import PgRegistry

        reg = PgRegistry()
        with reg._connect() as conn:
            rows = conn.execute("SELECT * FROM anchor_batches ORDER BY anchored_at").fetchall()
        for r in rows:
            yield (r["batch_id"], r["merkle_root"], r["ots_receipt_id"], (r["meta"] or {}).get("leaf_order", []),
                   r["anchored_at"], lambda leaf: reg.proofs_by_leaf([leaf])[0])
    except Exception as e:
        print(f"(PostgreSQL skipped: {e})")

    legacy = ROOT / "artifacts" / "por_registry.sqlite3"
    if legacy.exists():
        conn = sqlite3.connect(legacy)
        conn.row_factory = sqlite3.Row

        def lite_proof(leaf):
            return json.loads(conn.execute("SELECT proof_json FROM proofs WHERE leaf_digest = ?", (leaf,)).fetchone()["proof_json"])

        for r in conn.execute("SELECT * FROM anchors ORDER BY created_at").fetchall():
            meta = json.loads(r["meta_json"] or "{}")
            yield (r["batch_id"], r["merkle_root"], r["ots_receipt_id"], meta.get("leaf_order", []),
                   datetime.fromtimestamp(r["created_at"]), lite_proof)


def main() -> None:
    for batch_id, root, receipt_id, leaves, when, lookup in batches():
        path = export_batch(OUT, batch_id, root, str(RECEIPTS / f"{receipt_id}.ots"), leaves, when, lookup)
        if path:
            print(f"{path.name}(.ots)   root {root[:16]}…  ({len(leaves)} record(s))")
        else:
            print(f"skip {batch_id}: missing receipt/leaves or data does not hash to the root")
    print(f"\nFiles in {OUT}\nOn https://opentimestamps.org drag the .ots file, then its .bin file, into Stamp & Verify.")


if __name__ == "__main__":
    main()
