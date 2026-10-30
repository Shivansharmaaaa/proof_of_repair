"""Phones / cars / appliances: proof format, legacy compatibility, retrieval grounding."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.kb.catalog import classify_issue  # noqa: E402
from src.kb.retrieval import MemoryRetriever  # noqa: E402
from src.llm.multidomain import build_prompt, merge_with_reference, reference_report  # noqa: E402
from src.por.proof import ModelProvenance, ProofOfRepair, RepairReport, build_proof, canonical_dumps, sha256_hex  # noqa: E402
from src.por.verify import verify_leaf_digest, verify_report_hash  # noqa: E402

KB = ROOT / "data/processed/repair_kb.jsonl"
MODEL = ModelProvenance(model_name="test", model_version="t1")


def _report(code="PH-BATT"):
    return RepairReport(
        fault_code=code, diagnosis="Battery fault", severity="medium", parts=["Battery"],
        repair_steps=["Replace battery"], qa_checks=["Health 100%"], estimated_minutes=40,
    )


def test_phone_proof_roundtrip_and_tamper():
    por = build_proof(asset_type="phone", asset_id="356938035643809", device="Apple iPhone 6",
                      usage_value=812, report=_report(), evidence_cid="cid", model=MODEL)
    assert por.usage_unit == "battery_cycles"
    again = ProofOfRepair.from_dict(por.to_dict())
    assert verify_report_hash(again) and verify_leaf_digest(again)
    assert not verify_leaf_digest(replace(again, usage_value=10))  # rolled-back battery cycles
    assert not verify_leaf_digest(replace(again, asset_type="car"))


def test_legacy_vehicle_record_still_verifies():
    """Records sealed before the multi-domain change used a vin/vehicle/odometer leaf."""
    import hashlib
    import json

    report = _report("P0420").to_dict()
    legacy = {
        "proof_id": "legacy-1", "vin": "1HGBH41JXMN109186", "vehicle": "2016 Honda Civic",
        "odometer_km": 98000, "event_type": "REPAIR", "issuer_id": "w", "timestamp": 1.0,
        "report": report, "evidence_cid": "cid", "report_hash": sha256_hex(canonical_dumps(report)),
        "model": {}, "extra": {},
    }
    payload = {k: legacy[k] for k in ("proof_id", "vin", "vehicle", "odometer_km", "event_type", "issuer_id",
                                      "timestamp", "report_hash", "evidence_cid", "model", "extra")}
    legacy["leaf_digest"] = hashlib.sha256(b"\x00" + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    por = ProofOfRepair.from_dict(legacy)
    assert por.schema_version == 1 and por.vin == "1HGBH41JXMN109186"
    assert verify_leaf_digest(por)


def test_issue_classification():
    assert classify_issue("phone", "Screen is cracked, touch dead").fault_code == "PH-DISP"
    assert classify_issue("appliance", "shows error", "OE").fault_code == "AP-WATER"
    assert classify_issue("appliance", "Turns on but does not heat the water").fault_code == "AP-HEAT"
    assert classify_issue("car", "Grinding noise when braking").fault_code == "CR-BRAKE"


@pytest.mark.skipif(not KB.exists(), reason="run scripts/prepare_multidomain.py first")
def test_demo_cases_ground_on_matching_guides():
    kb = MemoryRetriever.from_jsonl(KB)
    expect = {
        ("phone", "Apple iPhone 6", "Battery drains very fast and the phone shuts down at around 20%", ""): "ifixit-29363",
        ("car", "2016 Honda Civic", "Check engine light on, failed emissions", "P0420"): "mechanicdb-P0420",
        ("appliance", "Kenmore 110 Series Washing Machine", "Water does not drain at the end of the cycle", ""): "ifixit-11043",
        ("appliance", "Ninja Coffee Bar CF086", "Turns on but does not heat the water", ""): "ifixit-98487",
    }
    for args, ref_id in expect.items():
        assert kb.best(*args).ref_id == ref_id, args


@pytest.mark.skipif(not KB.exists(), reason="run scripts/prepare_multidomain.py first")
def test_grounded_report_survives_bad_model_output():
    kb = MemoryRetriever.from_jsonl(KB)
    ref = kb.best("phone", "Samsung Galaxy S7", "Screen cracked", "")
    grounded = reference_report("phone", "Samsung Galaxy S7", "Screen cracked", "", ref)
    merged = merge_with_reference({"fault_code": "PH-DISP", "repair_steps": ["x x x x x x x x x x"] * 1}, grounded)
    assert merged["fault_code"] == "PH-DISP"
    assert merged["repair_steps"] == grounded["repair_steps"]  # one junk step is rejected
    assert ref.ref_id in build_prompt("phone", "Samsung Galaxy S7", "Screen cracked", ref=ref)


def test_api_rejects_bad_identifiers():
    from pydantic import ValidationError

    from src.cloud.api import DiagnoseRequest

    ok = DiagnoseRequest(asset_type="phone", asset_id="356938035643809", device="iPhone 6", issue="battery")
    assert ok.asset_id == "356938035643809"
    with pytest.raises(ValidationError):
        DiagnoseRequest(asset_type="phone", asset_id="356938035643808", device="iPhone 6", issue="battery")
    with pytest.raises(ValidationError):
        DiagnoseRequest(asset_type="car", asset_id="1HGBH41JXMN1O9186", device="Civic", issue="cel")
    legacy = DiagnoseRequest(vin="1HGBH41JXMN109186", vehicle="2016 Honda Civic", odometer_km=98000, symptoms="cel")
    assert legacy.asset_type == "car" and legacy.usage_value == 98000
