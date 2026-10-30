"""PostgreSQL registry: devices, sealed repair records, anchor batches, repair knowledge base.

Same interface as the SQLite VinRegistry, plus:
- per-record Merkle inclusion proofs, so verification works after a restart;
- repair_guides (iFixit + MechanicDB) with a full-text index used to ground the LLM.

Connection string: DATABASE_URL (default postgresql://localhost/proof_of_repair).
Any managed Postgres (Supabase, Neon, RDS, Cloud SQL) works by changing DATABASE_URL.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from src.kb.catalog import IDENTIFIER_KIND, Guide, classify_issue, extract_dtc
from src.kb.retrieval import tokens

DEFAULT_URL = "postgresql://localhost/proof_of_repair"

SCHEMA = """
CREATE TABLE IF NOT EXISTS repair_guides (
    ref_id       TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    asset_type   TEXT NOT NULL,
    family       TEXT,
    device       TEXT,
    title        TEXT NOT NULL,
    subject      TEXT,
    component    TEXT,
    fault_code   TEXT,
    steps        JSONB NOT NULL,
    tools        JSONB,
    parts        JSONB,
    url          TEXT,
    est_minutes  INTEGER,
    description  TEXT,
    search       TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(device, '') || ' ' || coalesce(title, '') || ' ' ||
                              coalesce(family, '') || ' ' || coalesce(subject, ''))
    ) STORED
);
CREATE INDEX IF NOT EXISTS idx_guides_search ON repair_guides USING GIN (search);
CREATE INDEX IF NOT EXISTS idx_guides_type_comp ON repair_guides (asset_type, component);
CREATE INDEX IF NOT EXISTS idx_guides_fault ON repair_guides (fault_code);

CREATE TABLE IF NOT EXISTS assets (
    asset_id         TEXT PRIMARY KEY,
    asset_type       TEXT NOT NULL CHECK (asset_type IN ('phone', 'car', 'appliance')),
    identifier_kind  TEXT NOT NULL,
    device           TEXT,
    first_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repair_records (
    proof_id        UUID PRIMARY KEY,
    asset_id        TEXT NOT NULL REFERENCES assets(asset_id),
    asset_type      TEXT NOT NULL,
    device          TEXT,
    usage_value     INTEGER,
    usage_unit      TEXT,
    event_type      TEXT,
    issuer_id       TEXT,
    sealed_at       TIMESTAMPTZ NOT NULL,
    fault_code      TEXT,
    severity        TEXT,
    diagnosis       TEXT,
    reference_guide TEXT REFERENCES repair_guides(ref_id),
    engine          TEXT,
    model_version   TEXT,
    leaf_digest     CHAR(64) UNIQUE NOT NULL,
    report_hash     CHAR(64) NOT NULL,
    evidence_cid    TEXT,
    report          JSONB NOT NULL,
    proof           JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_records_asset ON repair_records (asset_id, sealed_at);

CREATE TABLE IF NOT EXISTS anchor_batches (
    batch_id          TEXT PRIMARY KEY,
    merkle_root       CHAR(64) NOT NULL,
    leaf_count        INTEGER NOT NULL,
    chain_mode        TEXT,
    chain_network     TEXT,
    chain_id          BIGINT,
    chain_tx          TEXT,
    block_number      BIGINT,
    contract_address  TEXT,
    explorer_url      TEXT,
    ots_receipt_id    TEXT,
    ots_status        TEXT,
    ots_mode          TEXT,
    meta              JSONB,
    anchored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_batches_root ON anchor_batches (merkle_root);

CREATE TABLE IF NOT EXISTS record_anchors (
    proof_id      UUID NOT NULL REFERENCES repair_records(proof_id),
    batch_id      TEXT NOT NULL REFERENCES anchor_batches(batch_id),
    leaf_index    INTEGER,
    merkle_proof  JSONB,
    PRIMARY KEY (proof_id, batch_id)
);

CREATE OR REPLACE VIEW v_device_history AS
SELECT r.asset_id, r.asset_type, r.device, r.usage_value, r.usage_unit,
       r.fault_code, r.severity, r.sealed_at, r.issuer_id, r.reference_guide,
       r.leaf_digest, b.merkle_root, b.chain_network, b.chain_tx, b.block_number,
       b.explorer_url, b.ots_status, b.anchored_at
FROM repair_records r
LEFT JOIN record_anchors ra ON ra.proof_id = r.proof_id
LEFT JOIN anchor_batches b ON b.batch_id = ra.batch_id
ORDER BY r.sealed_at DESC;
"""


def norm_id(asset_id: str) -> str:
    return (asset_id or "").strip().upper()


def _ts(epoch: Any) -> datetime:
    return datetime.fromtimestamp(float(epoch or 0), tz=timezone.utc)


class PgRegistry:
    backend = "postgresql"

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.environ.get("DATABASE_URL") or DEFAULT_URL
        with self._connect() as conn:
            conn.execute(SCHEMA)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.url, autocommit=True, row_factory=dict_row)

    # ---- knowledge base -------------------------------------------------
    def load_guides(self, guides: Iterable[Guide]) -> int:
        rows = [
            (
                g.ref_id, g.source, g.asset_type, g.family, g.device, g.title, g.subject,
                g.component, g.fault_code, Jsonb(g.steps), Jsonb(g.tools), Jsonb(g.parts),
                g.url, g.est_minutes, g.description,
            )
            for g in guides
        ]
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO repair_guides (ref_id, source, asset_type, family, device, title, subject,
                    component, fault_code, steps, tools, parts, url, est_minutes, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ref_id) DO UPDATE SET
                    title = EXCLUDED.title, subject = EXCLUDED.subject, component = EXCLUDED.component,
                    fault_code = EXCLUDED.fault_code, steps = EXCLUDED.steps, tools = EXCLUDED.tools,
                    parts = EXCLUDED.parts, est_minutes = EXCLUDED.est_minutes,
                    description = EXCLUDED.description
                """,
                rows,
            )
        return len(rows)

    @staticmethod
    def _guide(row: Dict[str, Any]) -> Guide:
        data = {k: row[k] for k in Guide.__dataclass_fields__ if k in row}
        for key in ("family", "device", "subject", "component", "fault_code", "url", "description"):
            data[key] = data.get(key) or ""
        data["est_minutes"] = data.get("est_minutes") or 0
        return Guide.from_dict(data)

    def get_guide(self, ref_id: str) -> Optional[Guide]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM repair_guides WHERE ref_id = %s", (ref_id,)).fetchone()
        return self._guide(row) if row else None

    def best_guide(self, asset_type: str, device: str, issue: str, error_code: str = "") -> Optional[Guide]:
        """OBD code -> MechanicDB row; else component filter + full-text rank on the device name."""
        with self._connect() as conn:
            if asset_type == "car":
                dtc = extract_dtc(error_code) or extract_dtc(issue)
                if dtc:
                    row = conn.execute(
                        "SELECT * FROM repair_guides WHERE source = 'MechanicDB' AND fault_code = %s",
                        (dtc,),
                    ).fetchone()
                    if row:
                        return self._guide(row)
            comp = classify_issue(asset_type, issue, error_code)
            # Score = matched device tokens (model numbers count double), then issue overlap.
            dev_terms = list(dict.fromkeys(t for t in tokens(device) if len(t) > 1 or t.isdigit()))
            score_sql = " + ".join(
                f"(CASE WHEN search @@ to_tsquery('simple', %(d{i})s) THEN {2 if any(c.isdigit() for c in t) else 1} ELSE 0 END)"
                for i, t in enumerate(dev_terms)
            ) or "0"
            params: Dict[str, Any] = {f"d{i}": t for i, t in enumerate(dev_terms)}
            params["iss"] = " | ".join(dict.fromkeys(t for t in tokens(issue) if len(t) > 3)) or "x"
            params["t"] = asset_type
            for component in (comp.key, None):
                params["c"] = component
                row = conn.execute(
                    f"""
                    SELECT *, ({score_sql}) AS dev_score,
                              ts_rank(search, to_tsquery('simple', %(iss)s)) AS issue_rank
                    FROM repair_guides
                    WHERE asset_type = %(t)s AND source <> 'MechanicDB'
                      AND (%(c)s::text IS NULL OR component = %(c)s)
                    ORDER BY dev_score DESC, length(coalesce(device, '')) ASC,
                             length(coalesce(subject, '')) ASC, issue_rank DESC,
                             jsonb_array_length(steps) ASC
                    LIMIT 1
                    """,
                    params,
                ).fetchone()
                if row:
                    return self._guide(row)
        return None

    # ---- repair records -------------------------------------------------
    def upsert_proof(self, por: Dict[str, Any]) -> None:
        report = por.get("report") or {}
        extra = por.get("extra") or {}
        model = por.get("model") or {}
        asset_id = norm_id(por.get("asset_id") or por.get("vin", ""))
        asset_type = por.get("asset_type") or "car"
        device = por.get("device") or por.get("vehicle")
        ref_id = extra.get("reference_guide") or None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assets (asset_id, asset_type, identifier_kind, device)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (asset_id) DO UPDATE SET last_seen = now(),
                    device = COALESCE(EXCLUDED.device, assets.device)
                """,
                (asset_id, asset_type, IDENTIFIER_KIND.get(asset_type, "ID"), device),
            )
            if ref_id and not conn.execute(
                "SELECT 1 FROM repair_guides WHERE ref_id = %s", (ref_id,)
            ).fetchone():
                ref_id = None
            conn.execute(
                """
                INSERT INTO repair_records (proof_id, asset_id, asset_type, device, usage_value, usage_unit,
                    event_type, issuer_id, sealed_at, fault_code, severity, diagnosis, reference_guide,
                    engine, model_version, leaf_digest, report_hash, evidence_cid, report, proof)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (proof_id) DO UPDATE SET proof = EXCLUDED.proof, report = EXCLUDED.report
                """,
                (
                    por["proof_id"], asset_id, asset_type, device,
                    por.get("usage_value", por.get("odometer_km")), por.get("usage_unit", "km"),
                    por.get("event_type"), por.get("issuer_id"), _ts(por.get("timestamp")),
                    report.get("fault_code"), report.get("severity"), report.get("diagnosis"), ref_id,
                    extra.get("engine"), model.get("model_version"), por.get("leaf_digest"),
                    por.get("report_hash"), por.get("evidence_cid"), Jsonb(report), Jsonb(por),
                ),
            )

    def get_proof(self, proof_id: str) -> Optional[Dict[str, Any]]:
        """Rebuild the record from the table columns, so an edit to any visible column is caught on verify."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM repair_records WHERE proof_id::text = %s", (proof_id,)
            ).fetchone()
        if not row:
            return None
        por = dict(row["proof"])
        report = dict(row["report"])
        for col in ("fault_code", "severity", "diagnosis"):
            report[col] = row[col]
        por.update(
            report=report,
            asset_id=row["asset_id"],
            asset_type=row["asset_type"],
            device=row["device"],
            usage_value=row["usage_value"],
            usage_unit=row["usage_unit"],
            issuer_id=row["issuer_id"],
            leaf_digest=row["leaf_digest"],
            report_hash=row["report_hash"],
            evidence_cid=row["evidence_cid"],
        )
        anchor = self.latest_anchor_for_proof(proof_id)
        if anchor:
            por["anchor"] = anchor
        return por

    def list_proofs(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT proof_id::text AS id, proof FROM repair_records ORDER BY sealed_at").fetchall()
        out = []
        for row in rows:
            por = dict(row["proof"])
            anchor = self.latest_anchor_for_proof(row["id"])
            if anchor:
                por["anchor"] = anchor
            out.append(por)
        return out

    # ---- anchoring ------------------------------------------------------
    def save_anchor(
        self,
        batch_id: str,
        merkle_root: str,
        leaf_digests: List[str],
        ots_receipt: Optional[Dict[str, Any]] = None,
        chain_tx: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
        merkle_proofs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        ots = ots_receipt or {}
        chain = chain_tx if isinstance(chain_tx, dict) else {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO anchor_batches (batch_id, merkle_root, leaf_count, chain_mode, chain_network,
                    chain_id, chain_tx, block_number, contract_address, explorer_url,
                    ots_receipt_id, ots_status, ots_mode, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (batch_id) DO NOTHING
                """,
                (
                    batch_id, merkle_root, len(leaf_digests), chain.get("mode"), chain.get("network"),
                    chain.get("chain_id"), chain.get("tx_hash"), chain.get("block_number"),
                    chain.get("contract_address"), chain.get("explorer_url"),
                    ots.get("receipt_id"), ots.get("status"), ots.get("mode"),
                    Jsonb({"leaf_order": leaf_digests, **(meta or {})}),
                ),
            )
            for idx, leaf in enumerate(leaf_digests):
                row = conn.execute(
                    "SELECT proof_id FROM repair_records WHERE leaf_digest = %s", (leaf,)
                ).fetchone()
                if not row:
                    continue
                mp = (merkle_proofs or {}).get(leaf)
                conn.execute(
                    """
                    INSERT INTO record_anchors (proof_id, batch_id, leaf_index, merkle_proof)
                    VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
                    """,
                    (row["proof_id"], batch_id, idx, Jsonb(mp) if mp else None),
                )
        return self._anchor_dict(self._batch(batch_id))

    def _batch(self, batch_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM anchor_batches WHERE batch_id = %s", (batch_id,)).fetchone()

    @staticmethod
    def _anchor_dict(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not row:
            return {}
        return {
            "batch_id": row["batch_id"],
            "merkle_root": row["merkle_root"],
            "ots_receipt_id": row["ots_receipt_id"],
            "ots_status": row["ots_status"],
            "ots_mode": row["ots_mode"],
            "chain_tx": row["chain_tx"],
            "chain_network": row["chain_network"],
            "chain_mode": row["chain_mode"],
            "block_number": row["block_number"],
            "explorer_url": row["explorer_url"],
        }

    def latest_anchor_for_proof(self, proof_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT b.* FROM anchor_batches b
                JOIN record_anchors ra ON ra.batch_id = b.batch_id
                WHERE ra.proof_id::text = %s
                ORDER BY b.anchored_at DESC LIMIT 1
                """,
                (proof_id,),
            ).fetchone()
        return self._anchor_dict(row) or None

    def proofs_by_leaf(self, leaf_digests: Iterable[str]) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT proof FROM repair_records WHERE leaf_digest = ANY(%s)", (list(leaf_digests),)
            ).fetchall()
        return [dict(r["proof"]) for r in rows]

    def unanchored_leaves(self) -> List[str]:
        """Sealed records not yet in any anchor batch (restores the pending queue after a restart)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.leaf_digest FROM repair_records r
                WHERE NOT EXISTS (SELECT 1 FROM record_anchors ra WHERE ra.proof_id = r.proof_id)
                ORDER BY r.sealed_at
                """
            ).fetchall()
        return [r["leaf_digest"] for r in rows]

    def merkle_proof_for_leaf(self, leaf_digest: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ra.merkle_proof FROM record_anchors ra
                JOIN repair_records r ON r.proof_id = ra.proof_id
                WHERE r.leaf_digest = %s AND ra.merkle_proof IS NOT NULL
                ORDER BY ra.batch_id DESC LIMIT 1
                """,
                (leaf_digest,),
            ).fetchone()
        return dict(row["merkle_proof"]) if row else None

    # ---- buyer lookup ---------------------------------------------------
    def asset_timeline(self, asset_id: str) -> Dict[str, Any]:
        aid = norm_id(asset_id)
        with self._connect() as conn:
            asset = conn.execute("SELECT * FROM assets WHERE asset_id = %s", (aid,)).fetchone()
            rows = conn.execute(
                "SELECT proof_id::text AS id, proof, reference_guide FROM repair_records WHERE asset_id = %s ORDER BY sealed_at",
                (aid,),
            ).fetchall()
        timeline = []
        for row in rows:
            p = row["proof"]
            report = p.get("report") or {}
            anchor = self.latest_anchor_for_proof(row["id"]) or {}
            timeline.append(
                {
                    "proof_id": p.get("proof_id"),
                    "when": p.get("timestamp"),
                    "asset_type": p.get("asset_type", "car"),
                    "device": p.get("device") or p.get("vehicle"),
                    "usage_value": p.get("usage_value", p.get("odometer_km")),
                    "usage_unit": p.get("usage_unit", "km"),
                    "issuer_id": p.get("issuer_id"),
                    "event_type": p.get("event_type"),
                    "fault_code": report.get("fault_code"),
                    "severity": report.get("severity"),
                    "diagnosis": report.get("diagnosis"),
                    "parts": report.get("parts") or [],
                    "buyer_advice": report.get("buyer_advice"),
                    "reference_guide": row["reference_guide"],
                    "leaf_digest": p.get("leaf_digest"),
                    "evidence_cid": p.get("evidence_cid"),
                    "anchored": bool(anchor.get("merkle_root")),
                    "anchor": anchor,
                }
            )
        return {
            "asset_id": aid,
            "vin": aid,
            "asset_type": asset["asset_type"] if asset else None,
            "identifier_kind": asset["identifier_kind"] if asset else None,
            "device": asset["device"] if asset else None,
            "count": len(timeline),
            "anchored_count": sum(1 for e in timeline if e["anchored"]),
            "timeline": timeline,
            "trust_summary": (
                "verified_timeline" if timeline and all(e["anchored"] for e in timeline)
                else "partial" if any(e["anchored"] for e in timeline)
                else "sealed_only" if timeline
                else "empty"
            ),
            "storage": "postgresql",
        }

    vin_timeline = asset_timeline

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            q = lambda sql: conn.execute(sql).fetchone()["n"]  # noqa: E731
            return {
                "backend": "postgresql",
                "url": self.url.split("@")[-1],
                "proofs": q("SELECT COUNT(*) AS n FROM repair_records"),
                "assets": q("SELECT COUNT(*) AS n FROM assets"),
                "vins": q("SELECT COUNT(*) AS n FROM assets"),
                "anchors": q("SELECT COUNT(*) AS n FROM anchor_batches"),
                "guides": q("SELECT COUNT(*) AS n FROM repair_guides"),
            }
