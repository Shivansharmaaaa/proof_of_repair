"""FastAPI service: cloud Proof of Repair for phones, cars and home appliances + web UI."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, Field, model_validator

from src.blockchain.anchoring import AnchoringService, load_calendar
from src.blockchain.evm_ledger import load_ledger
from src.blockchain.ots_export import export_batch
from src.cloud.registry import VinRegistry, norm_vin
from src.cloud.storage import EvidenceStore
from src.kb.catalog import IDENTIFIER_KIND, Guide
from src.kb.retrieval import MemoryRetriever
from src.por.proof import EventType, ModelProvenance, ProofOfRepair, build_proof
from src.por.verify import verify_full

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
OTS_PUBLIC = ROOT / "artifacts" / "ots_public"

app = FastAPI(
    title="Proof of Repair API",
    description="Cloud Proof of Repair for phones, cars and home appliances: LLM diagnosis grounded on "
    "real repair manuals, PostgreSQL registry, Merkle batching, Ethereum + OpenTimestamps anchoring.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _open_registry():
    """PostgreSQL by default (DATABASE_URL); SQLite file if Postgres is unreachable or DB_BACKEND=sqlite."""
    if os.environ.get("DB_BACKEND", "postgres").lower() != "sqlite":
        try:
            from src.cloud.pg_registry import PgRegistry

            return PgRegistry()
        except Exception as e:  # pragma: no cover - depends on local services
            print(f"[registry] PostgreSQL unavailable ({e}); falling back to SQLite")
    reg = VinRegistry(os.environ.get("SQLITE_PATH") or ROOT / "artifacts" / "por_registry.sqlite3")
    if reg.stats()["proofs"] == 0:
        reg.migrate_jsonl(ROOT / "artifacts" / "vin_registry")
    return reg


store = EvidenceStore(ROOT / "artifacts" / "evidence")
ledger = load_ledger()
calendar = load_calendar(ROOT / "artifacts" / "ots_calendar")
anchoring = AnchoringService(calendar=calendar, ledger=ledger)
registry = _open_registry()
_kb_file = ROOT / "data" / "processed" / "repair_kb.jsonl"
memory_kb = MemoryRetriever.from_jsonl(_kb_file) if _kb_file.exists() else MemoryRetriever([])

engines: Dict[str, Any] = {}
# Sealed records survive a restart: re-queue anything not yet batched.
pending_leaves: List[str] = list(getattr(registry, "unanchored_leaves", lambda: [])())
last_batch: Dict[str, Any] = {}

MULTIDOMAIN_ADAPTER = ROOT / "artifacts/adapters/multidomain-mlx-lora"

DEMO_CASES = [
    {
        "asset_type": "phone",
        "label": "iPhone 6 · battery",
        "asset_id": "356938035643809",
        "device": "Apple iPhone 6",
        "usage_value": 812,
        "error_code": "",
        "issue": "Battery drains very fast and the phone shuts down at around 20%",
        "notes": "Battery health shows 71% (service); second-hand unit",
    },
    {
        "asset_type": "phone",
        "label": "Galaxy S7 · screen",
        "asset_id": "352099001761481",
        "device": "Samsung Galaxy S7",
        "usage_value": 640,
        "error_code": "",
        "issue": "Screen is cracked and touch does not respond in the lower half",
        "notes": "Dropped on concrete; display still lights up",
    },
    {
        "asset_type": "car",
        "label": "Civic · P0420",
        "asset_id": "1HGBH41JXMN109186",
        "device": "2016 Honda Civic",
        "usage_value": 98000,
        "error_code": "P0420",
        "issue": "Check engine light on, failed emissions, slight sulfur smell from exhaust",
        "notes": "STFT/LTFT near trim limits; rear O2 voltage lazy",
    },
    {
        "asset_type": "car",
        "label": "Focus · brakes",
        "asset_id": "1FAHP34N06W123456",
        "device": "2006 Ford Focus",
        "usage_value": 121000,
        "error_code": "",
        "issue": "Grinding noise when braking and longer stopping distance",
        "notes": "Rear drums, front pads near wear indicator",
    },
    {
        "asset_type": "appliance",
        "label": "Kenmore washer · drain",
        "asset_id": "KM110-CW4417",
        "device": "Kenmore 110 Series Washing Machine",
        "usage_value": 1450,
        "error_code": "",
        "issue": "Water does not drain at the end of the cycle",
        "notes": "Pump hums but no water moves",
    },
    {
        "asset_type": "appliance",
        "label": "Ninja coffee · no heat",
        "asset_id": "NJ-CF086-55120",
        "device": "Ninja Coffee Bar CF086",
        "usage_value": 2100,
        "error_code": "",
        "issue": "Turns on but does not heat the water",
        "notes": "Power light on; brew is cold",
    },
]


def get_engine(name: str = "multidomain"):
    name = (name or "multidomain").lower().strip()
    if name in {"auto", "mistral"}:
        name = "multidomain"
    if name in engines:
        return engines[name], name
    if name == "tinyllama":
        from src.llm.infer import DiagnosticEngine

        adapter = ROOT / "artifacts/adapters/vehicle-lora-dtc"
        if not (adapter / "adapter_config.json").exists():
            adapter = ROOT / "artifacts/adapters/vehicle-lora"
        if not (adapter / "adapter_config.json").exists():
            raise HTTPException(400, f"TinyLlama adapter missing at {adapter}")
        eng = DiagnosticEngine(adapter_dir=adapter)
    elif name == "multidomain":
        from src.llm.multidomain import MultiDomainEngine

        eng = MultiDomainEngine(adapter_path=MULTIDOMAIN_ADAPTER)
    else:
        raise HTTPException(400, f"unknown engine {name}")
    engines[name] = eng
    return eng, name


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


class DiagnoseRequest(BaseModel):
    asset_type: Literal["phone", "car", "appliance"] = "car"
    asset_id: str = Field(..., min_length=4, max_length=40, validation_alias=AliasChoices("asset_id", "vin"))
    device: str = Field(..., min_length=2, validation_alias=AliasChoices("device", "vehicle"))
    usage_value: int = Field(0, ge=0, validation_alias=AliasChoices("usage_value", "odometer_km"))
    issue: str = Field(..., min_length=3, validation_alias=AliasChoices("issue", "symptoms"))
    error_code: str = Field("", validation_alias=AliasChoices("error_code", "dtc_codes"))
    notes: str = Field("", validation_alias=AliasChoices("notes", "sensor_notes"))
    issuer_id: str = "certified-workshop"
    engine: str = "multidomain"

    @model_validator(mode="after")
    def check_identifier(self) -> "DiagnoseRequest":
        aid = self.asset_id.strip().upper()
        if self.asset_type == "phone":
            if not re.fullmatch(r"\d{15}", aid) or not _luhn_ok(aid):
                raise ValueError("IMEI must be 15 digits with a valid check digit (dial *#06#)")
        elif self.asset_type == "car":
            if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{11,17}", aid):
                raise ValueError("VIN must be 11-17 letters/digits (no I, O or Q)")
        elif not re.fullmatch(r"[A-Z0-9][A-Z0-9\-/.]{3,39}", aid):
            raise ValueError("Serial number must be 4-40 letters, digits or - / .")
        self.asset_id = aid
        return self


class AnchorBatchRequest(BaseModel):
    batch_id: str = "ui-batch-001"
    leaf_digests: Optional[List[str]] = None


class VerifyRequest(BaseModel):
    proof: Dict[str, Any]
    merkle_proof: Optional[Dict[str, Any]] = None


def find_reference(asset_type: str, device: str, issue: str, error_code: str) -> Optional[Guide]:
    if hasattr(registry, "best_guide"):
        try:
            ref = registry.best_guide(asset_type, device, issue, error_code)
            if ref is not None:
                return ref
        except Exception as e:  # pragma: no cover
            print(f"[kb] postgres retrieval failed ({e}); using in-memory index")
    return memory_kb.best(asset_type, device, issue, error_code)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    chain: Dict[str, Any] = {"mode": "in_memory_simulator"}
    if hasattr(ledger, "status"):
        try:
            chain = ledger.status()
        except Exception as e:
            chain = {"mode": "error", "detail": str(e)}
    elif ledger.__class__.__name__ == "InMemoryLedger":
        chain = {
            "mode": "in_memory_simulator",
            "note": "Run bash scripts/start_live_chain.sh for a real local EVM",
        }
    ots: Dict[str, Any] = {"mode": "unknown"}
    if hasattr(calendar, "status"):
        try:
            ots = calendar.status()
        except Exception as e:
            ots = {"mode": "error", "detail": str(e)}
    stats = registry.stats()
    return {
        "status": "ok",
        "domain": "phones_cars_appliances_por",
        "engines": {
            "multidomain": True,
            "multidomain_adapter": (MULTIDOMAIN_ADAPTER / "adapters.safetensors").exists(),
            "tinyllama": (ROOT / "artifacts/adapters/vehicle-lora-dtc/adapter_config.json").exists(),
        },
        "chain": chain,
        "ots": ots,
        "storage": stats,
        "pending_leaves": len(pending_leaves),
        "proofs": stats["proofs"],
    }


@app.get("/api/demo_cases")
def demo_cases() -> List[Dict[str, Any]]:
    return DEMO_CASES


@app.get("/api/kb_stats")
def kb_stats() -> Dict[str, int]:
    """Repair procedures available per device type (iFixit guides + OBD-II codes)."""
    counts: Dict[str, int] = {}
    for g in memory_kb.guides:
        counts[g.asset_type] = counts.get(g.asset_type, 0) + 1
    return counts


@app.get("/api/guides/search")
def guide_search(asset_type: str, device: str, issue: str, error_code: str = "") -> Dict[str, Any]:
    """Show which real repair procedure would ground a diagnosis."""
    ref = find_reference(asset_type, device, issue, error_code)
    return {"reference": ref.to_dict() if ref else None}


@app.post("/api/diagnose_and_prove")
def diagnose_and_prove(req: DiagnoseRequest) -> Dict[str, Any]:
    if req.engine.lower() == "tinyllama" and req.asset_type != "car":
        raise HTTPException(400, "TinyLlama adapter is trained on vehicles only; use the multi-domain engine")
    eng, engine_name = get_engine(req.engine)
    ref = find_reference(req.asset_type, req.device, req.issue, req.error_code)
    started = time.time()
    if engine_name == "multidomain":
        report = eng.diagnose_asset(
            asset_type=req.asset_type,
            device=req.device,
            issue=req.issue,
            error_code=req.error_code,
            notes=req.notes,
            ref=ref,
        )
    else:
        report = eng.diagnose(
            vehicle=req.device,
            symptoms=req.issue,
            dtc_codes=req.error_code,
            sensor_notes=req.notes,
        )
    reference = (
        {"ref_id": ref.ref_id, "source": ref.source, "title": ref.title, "url": ref.url}
        if ref
        else None
    )
    evidence_cid = store.put_json(
        {
            "asset_type": req.asset_type,
            "asset_id": req.asset_id,
            "identifier_kind": IDENTIFIER_KIND[req.asset_type],
            "device": req.device,
            "usage_value": req.usage_value,
            "issue": req.issue,
            "error_code": req.error_code,
            "notes": req.notes,
            "reference": reference,
            "report": report.to_dict(),
        },
        meta={"type": "repair_evidence", "asset_type": req.asset_type},
    )
    model = ModelProvenance(
        model_name=eng.model_name,
        model_version=eng.model_version,
        adapter_hash=getattr(eng, "adapter_hash", "") or "",
        dataset_merkle_root=getattr(eng, "dataset_merkle_root", "") or "",
        framework="mlx-lm" if engine_name == "multidomain" else "transformers+peft",
    )
    por = build_proof(
        asset_type=req.asset_type,
        asset_id=req.asset_id,
        device=req.device,
        usage_value=req.usage_value,
        report=report,
        evidence_cid=evidence_cid,
        model=model,
        issuer_id=req.issuer_id,
        event_type=EventType.REPAIR,
        extra={
            "audience": "second_hand_buyer",
            "engine": engine_name,
            "reference_guide": ref.ref_id if ref else None,
        },
    )
    pending_leaves.append(por.leaf_digest)
    record = por.to_dict()
    registry.upsert_proof(record)
    return {
        "engine": engine_name,
        "seconds": round(time.time() - started, 1),
        "reference": reference,
        "report": report.to_dict(),
        "proof": record,
        "pending_batch_size": len(pending_leaves),
    }


@app.post("/api/anchor_batch")
def anchor_batch(req: AnchorBatchRequest) -> Dict[str, Any]:
    leaves = req.leaf_digests if req.leaf_digests is not None else list(pending_leaves)
    if not leaves:
        raise HTTPException(400, "no leaves to anchor — seal at least one repair first")
    try:
        result = anchoring.anchor_batch(leaves, batch_id=req.batch_id)
    except Exception as e:
        raise HTTPException(502, f"anchoring failed: {e}")
    by_leaf = {}
    for p in (result.get("proofs") or {}).values():
        by_leaf[p["leaf_hash_hex"]] = p
    result["proofs_by_leaf"] = by_leaf
    result["leaf_order"] = list(leaves)
    global last_batch
    last_batch = result

    ots = result.get("ots_receipt") or {}
    chain = result.get("chain_tx") or {}
    batch_id = str(result.get("batch_id") or req.batch_id)
    registry.save_anchor(
        batch_id=batch_id,
        merkle_root=str(result.get("merkle_root")),
        leaf_digests=list(leaves),
        ots_receipt=ots if isinstance(ots, dict) else {},
        chain_tx=chain if isinstance(chain, dict) else {"tx_hash": chain},
        merkle_proofs=by_leaf,
    )
    # File pair for public verification on opentimestamps.org (Bitcoin timestamp).
    try:
        bin_path = export_batch(
            OTS_PUBLIC, batch_id, str(result.get("merkle_root")),
            ots.get("ots_file") if isinstance(ots, dict) else None, list(leaves), datetime.now(),
            lambda leaf: registry.proofs_by_leaf([leaf])[0],
        )
        if bin_path:
            result["ots_files"] = {"bin": str(bin_path), "ots": f"{bin_path}.ots", "folder": str(OTS_PUBLIC)}
    except Exception as e:  # never fail an anchor because of the convenience export
        print(f"[ots] export of verification files failed: {e}")

    if req.leaf_digests is None:
        pending_leaves.clear()
    return result


@app.post("/api/verify")
def verify_endpoint(body: VerifyRequest) -> Dict[str, Any]:
    por = ProofOfRepair.from_dict(body.proof)
    mp = body.merkle_proof
    if mp is None and last_batch.get("proofs_by_leaf"):
        mp = last_batch["proofs_by_leaf"].get(por.leaf_digest)
    if mp is None:
        mp = registry.merkle_proof_for_leaf(por.leaf_digest)
    results: Dict[str, Any] = verify_full(por, store=store, merkle_proof=mp, ledger=ledger)
    if mp is None:
        # Not batched yet: integrity checks ran, inclusion/anchor cannot be proven.
        results["merkle"] = False
        results["chain_anchor"] = False
        results["all_ok"] = False
    return results


@app.get("/api/proofs/{proof_id}/verify")
def verify_stored(proof_id: str) -> Dict[str, Any]:
    """Re-verify the record exactly as it is stored in the database right now."""
    por = registry.get_proof(proof_id)
    if not por:
        raise HTTPException(404, "proof not found")
    return verify_endpoint(VerifyRequest(proof=por))


@app.get("/api/proofs")
def list_proofs() -> List[Dict[str, Any]]:
    return registry.list_proofs()


@app.get("/api/asset/{asset_id}")
def asset_lookup(asset_id: str) -> Dict[str, Any]:
    """Buyer / dealer / insurer: repair timeline for an IMEI, VIN or serial number."""
    if len(norm_vin(asset_id)) < 4:
        raise HTTPException(400, "identifier too short")
    return registry.asset_timeline(asset_id)


@app.get("/api/vin/{vin}")
def vin_lookup(vin: str) -> Dict[str, Any]:
    return asset_lookup(vin)


@app.get("/api/proofs/{proof_id}")
def get_proof(proof_id: str) -> Dict[str, Any]:
    por = registry.get_proof(proof_id)
    if not por:
        raise HTTPException(404, "proof not found")
    return por


@app.get("/api/last_batch")
def get_last_batch() -> Dict[str, Any]:
    return last_batch or {}


# --- Static UI ---
if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/")
def index():
    index_path = FRONTEND / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "frontend missing")
    return FileResponse(index_path)


# Back-compat aliases used by older docs
@app.get("/health")
def health_alias():
    return health()


@app.post("/diagnose_and_prove")
def diagnose_alias(req: DiagnoseRequest):
    return diagnose_and_prove(req)
