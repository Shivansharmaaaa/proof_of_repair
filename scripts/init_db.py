"""Create the PostgreSQL database + schema and load the repair knowledge base.

Run: python scripts/init_db.py            (uses DATABASE_URL or postgresql://localhost/proof_of_repair)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cloud.pg_registry import DEFAULT_URL, PgRegistry  # noqa: E402
from src.kb.catalog import Guide  # noqa: E402


def ensure_database(url: str) -> None:
    db = url.rsplit("/", 1)[-1].split("?")[0]
    admin = url.rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{db}"')
            print(f"created database {db}")


def main() -> None:
    url = os.environ.get("DATABASE_URL") or DEFAULT_URL
    if "localhost" in url or "127.0.0.1" in url:
        ensure_database(url)
    reg = PgRegistry(url)
    if "--reset" in sys.argv:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("TRUNCATE record_anchors, anchor_batches, repair_records, assets")
        print("cleared repair records, anchors and assets (knowledge base kept)")
    kb_path = ROOT / "data/processed/repair_kb.jsonl"
    if not kb_path.exists():
        sys.exit("Missing data/processed/repair_kb.jsonl - run: python scripts/prepare_multidomain.py")
    guides = [Guide.from_dict(json.loads(l)) for l in kb_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = reg.load_guides(guides)
    stats = reg.stats()
    print(f"   database ready: {n} repair guides, {stats['proofs']} repair records, {stats['anchors']} anchor batches")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
