"""Proof of Repair — a tamper-evident record that binds a repair to one device.

A "device" is a car (VIN), phone (IMEI) or home appliance (serial number).

How a repair becomes a proof (see build_proof at the bottom):
    1. The AI repair report is turned into canonical JSON and hashed  -> report_hash
    2. The raw evidence is stored off-chain by its own hash           -> evidence_cid
    3. Everything important about the event (device, usage, report_hash,
       evidence_cid, AI model, workshop, time) is put into one payload
    4. That payload is hashed with a 0x00 prefix                       -> leaf_digest
    5. The leaf_digest later becomes one leaf of a Merkle tree whose root is
       anchored on the blockchain (see src/blockchain/merkle.py)

Changing ANY field afterwards changes the leaf_digest, so the record no longer
matches what was anchored — that is how tampering is detected.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(str, Enum):
    """Kind of lifecycle event being recorded for the device."""

    DIAGNOSIS = "DIAGNOSIS"
    REPAIR = "REPAIR"
    PARTS_REPLACE = "PARTS_REPLACE"
    PPI_PASS = "PPI_PASS"  # pre-purchase inspection
    OBD_CLEAR = "OBD_CLEAR"


def canonical_dumps(obj: Dict[str, Any]) -> str:
    """Serialise a dict to JSON in ONE fixed way so the same data always gives the same hash.

    Normal json.dumps can order keys differently or add spaces, which would change
    the hash even though the data is identical. sort_keys + no whitespace fixes that.
    Example: {"b": 1, "a": 2}  ->  '{"a":2,"b":1}'
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str | bytes) -> str:
    # SHA-256 fingerprint of text, returned as 64 hex characters.
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


@dataclass
class ModelProvenance:
    """Which AI produced the report, so a buyer can see exactly what model was used.

    adapter_hash pins the exact fine-tuned LoRA weights; dataset_merkle_root pins
    the exact training data. Both are part of the sealed leaf.
    """

    model_name: str
    model_version: str
    adapter_hash: str = ""
    dataset_merkle_root: str = ""
    framework: str = "transformers+peft"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairReport:
    """The structured repair report written by the fine-tuned LLM (or its grounded fallback)."""

    fault_code: str  # e.g. P0420 (car OBD-II), PH-BATT (phone battery), AP-WATER (appliance)
    diagnosis: str
    severity: str  # low / medium / high
    parts: List[str]
    repair_steps: List[str]
    qa_checks: List[str]  # checks done after the repair before sealing the record
    estimated_minutes: int
    confidence: float = 0.0
    buyer_advice: str = ""  # plain-language note for a second-hand buyer

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepairReport":
        # Rebuild a report from JSON (e.g. model output or database row), forcing correct types.
        return cls(
            fault_code=str(data["fault_code"]),
            diagnosis=str(data["diagnosis"]),
            severity=str(data["severity"]),
            parts=list(data.get("parts", [])),
            repair_steps=list(data.get("repair_steps", [])),
            qa_checks=list(data.get("qa_checks", [])),
            estimated_minutes=int(data.get("estimated_minutes", 0)),
            confidence=float(data.get("confidence", 0.0)),
            buyer_advice=str(data.get("buyer_advice", "")),
        )


# How "usage" is measured for each device type (sealed into the record so a
# seller cannot later roll back the odometer / battery cycle count).
USAGE_UNITS = {"car": "km", "phone": "battery_cycles", "appliance": "cycles"}


@dataclass
class ProofOfRepair:
    """One sealed repair record. This is what is stored in PostgreSQL and verified by buyers."""

    proof_id: str  # random UUID for this record
    asset_id: str  # VIN (car) / IMEI (phone) / serial number (appliance)
    device: str  # make + model
    usage_value: int  # odometer km / battery cycles / appliance cycles
    event_type: str
    issuer_id: str  # workshop / inspector
    timestamp: float  # Unix time when the record was sealed
    report: Dict[str, Any]  # the full RepairReport as a dict
    evidence_cid: str  # content address (hash) of the off-chain evidence bundle
    report_hash: str  # SHA-256 of the canonical report JSON
    model: Dict[str, Any]  # ModelProvenance as a dict
    leaf_digest: str = ""  # final fingerprint of the whole record (the Merkle leaf)
    extra: Dict[str, Any] = field(default_factory=dict)  # e.g. which repair manual was used
    asset_type: str = "car"
    usage_unit: str = "km"
    schema_version: int = 2  # 1 = legacy vehicle-only leaf layout

    # Legacy vehicle-only names, kept so older scripts keep working.
    @property
    def vin(self) -> str:
        return self.asset_id

    @property
    def vehicle(self) -> str:
        return self.device

    @property
    def odometer_km(self) -> int:
        return self.usage_value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofOfRepair":
        """Load a record from a dict, upgrading old car-only records (vin/vehicle/odometer_km)."""
        d = dict(data)
        if "asset_id" not in d and "vin" in d:
            # Old record: rename fields, but remember it is schema 1 so its leaf
            # is recomputed with the ORIGINAL field names and still verifies.
            d.setdefault("schema_version", 1)
            d["asset_id"] = d.pop("vin")
            d["device"] = d.pop("vehicle", "")
            d["usage_value"] = d.pop("odometer_km", 0)
        # Ignore unknown keys (e.g. database-only columns).
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def payload_for_leaf(self) -> Dict[str, Any]:
        """The exact set of fields that get committed into the leaf hash.

        Note the full report is NOT included directly — only its report_hash.
        That is enough: changing the report changes report_hash, which changes the leaf.
        leaf_digest itself is excluded (a hash cannot contain itself).
        """
        if self.schema_version == 1:
            # Legacy layout for records sealed before phones/appliances were added.
            return {
                "proof_id": self.proof_id,
                "vin": self.asset_id,
                "vehicle": self.device,
                "odometer_km": self.usage_value,
                "event_type": self.event_type,
                "issuer_id": self.issuer_id,
                "timestamp": self.timestamp,
                "report_hash": self.report_hash,
                "evidence_cid": self.evidence_cid,
                "model": self.model,
                "extra": self.extra,
            }
        return {
            "proof_id": self.proof_id,
            "asset_type": self.asset_type,
            "asset_id": self.asset_id,
            "device": self.device,
            "usage_value": self.usage_value,
            "usage_unit": self.usage_unit,
            "event_type": self.event_type,
            "issuer_id": self.issuer_id,
            "timestamp": self.timestamp,
            "report_hash": self.report_hash,
            "evidence_cid": self.evidence_cid,
            "model": self.model,
            "extra": self.extra,
        }

    def compute_leaf_digest(self) -> str:
        """leaf_digest = SHA-256(0x00 || canonical_json(payload)).

        The 0x00 prefix matches leaf_hash() in merkle.py, marking this as a LEAF
        (internal tree nodes use 0x01), so the digest drops straight into the tree.
        """
        payload = canonical_dumps(self.payload_for_leaf()).encode("utf-8")
        digest = hashlib.sha256(b"\x00" + payload).hexdigest()
        self.leaf_digest = digest
        return digest


def build_proof(
    report: RepairReport,
    evidence_cid: str,
    model: ModelProvenance,
    asset_id: str = "",
    device: str = "",
    usage_value: int = 0,
    asset_type: str = "car",
    issuer_id: str = "certified-workshop",
    event_type: EventType = EventType.REPAIR,
    extra: Optional[Dict[str, Any]] = None,
    vin: str = "",
    vehicle: str = "",
    odometer_km: Optional[int] = None,
) -> ProofOfRepair:
    """Seal a repair event to a device. vin/vehicle/odometer_km are legacy aliases for cars."""
    # Accept the old car-only argument names too.
    asset_id = asset_id or vin
    device = device or vehicle
    if odometer_km is not None and not usage_value:
        usage_value = odometer_km

    # Step 1: fingerprint the AI report.
    report_dict = report.to_dict()
    report_hash = sha256_hex(canonical_dumps(report_dict))

    # Step 2: assemble the record (evidence_cid was already computed by the evidence store).
    por = ProofOfRepair(
        proof_id=str(uuid.uuid4()),
        # Normalise the ID so "1hgcm..." and " 1HGCM... " refer to the same device.
        asset_id=asset_id.strip().upper(),
        device=device,
        usage_value=int(usage_value),
        event_type=event_type.value,
        issuer_id=issuer_id,
        timestamp=time.time(),
        report=report_dict,
        evidence_cid=evidence_cid,
        report_hash=report_hash,
        model=model.to_dict(),
        extra=extra or {},
        asset_type=asset_type,
        usage_unit=USAGE_UNITS.get(asset_type, "units"),
    )

    # Step 3: seal it — compute the leaf digest that will go into the Merkle tree.
    por.compute_leaf_digest()
    return por
