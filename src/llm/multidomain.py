"""Multi-domain (phone / car / appliance) repair diagnosis with Mistral-7B + LoRA (MLX).

The prompt is grounded on one retrieved reference procedure (iFixit guide or
MechanicDB DTC fixes). The same prompt builder is used for fine-tuning
(scripts/prepare_multidomain.py) and live inference, so the adapter sees the
exact format it was trained on.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.kb.catalog import (
    APPLIANCE_ERROR_CODES,
    COMPONENTS,
    IDENTIFIER_KIND,
    Guide,
    classify_issue,
    component_by_key,
    condensed_steps,
)
from src.llm.infer import collapse_runaway_text, is_runaway_text, parse_repair_json
from src.por.proof import RepairReport

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTER = ROOT / "artifacts" / "adapters" / "multidomain-mlx-lora"
DEFAULT_MODEL = str(
    Path.home()
    / ".cache/huggingface/hub/models--mlx-community--Mistral-7B-Instruct-v0.2-4bit"
    / "snapshots/64481e3a4a7bb0990c45c991958f8d6c00c1e785"
)
HF_MODEL_ID = "mlx-community/Mistral-7B-Instruct-v0.2-4bit"

SYSTEM_PROMPT = (
    "You are an expert repair technician assistant for a cloud Proof of Repair platform "
    "covering phones, cars and home appliances. Use the reference procedure when it is relevant. "
    "Reply with ONE complete valid JSON object only. No markdown. No prose before/after. "
    "Required keys: fault_code (string), diagnosis (string), severity (low|medium|high), "
    "parts (array of strings), repair_steps (array of strings), qa_checks (array of strings), "
    "estimated_minutes (integer), confidence (number 0-1), buyer_advice (string). "
    "Keep diagnosis under 300 characters and give 3-6 repair steps. Close all brackets."
)

BUYER_ADVICE = {
    "phone": "Before buying, dial *#06# and check the IMEI matches this sealed record, then test the {label} yourself.",
    "car": "Before buying, match the VIN on the dashboard with this sealed record and ask for the post-repair OBD scan.",
    "appliance": "Before buying, match the serial number on the rating plate with this sealed record and run one full cycle to test the {label}.",
}


def reference_block(ref: Optional[Guide]) -> str:
    if ref is None:
        return "Reference procedure: none found in the knowledge base."
    lines = [f"Reference procedure ({ref.source} {ref.ref_id}: {ref.title}):"]
    if ref.description:
        lines.append(f"Background: {ref.description}")
    lines += [f"- {s}" for s in condensed_steps(ref, limit=5)]
    if ref.parts:
        lines.append("Parts: " + ", ".join(ref.parts[:4]))
    if ref.tools:
        lines.append("Tools: " + ", ".join(ref.tools[:4]))
    return "\n".join(lines)


def build_prompt(
    asset_type: str,
    device: str,
    issue: str,
    error_code: str = "",
    notes: str = "",
    ref: Optional[Guide] = None,
) -> str:
    user = (
        f"Asset type: {asset_type}\n"
        f"Device: {device}\n"
        f"Identifier: {IDENTIFIER_KIND.get(asset_type, 'ID')}\n"
        f"Error code: {error_code or 'none'}\n"
        f"Reported issue: {issue}\n"
        f"Technician notes: {notes or 'none'}\n\n"
        f"{reference_block(ref)}\n\n"
        "Return complete JSON now."
    )
    return (
        f"### System\n{SYSTEM_PROMPT}\n\n"
        f"### User\nDiagnose this {asset_type} for a Proof of Repair record.\n\n{user}\n\n"
        "### Assistant\n"
    )


def reference_report(
    asset_type: str,
    device: str,
    issue: str,
    error_code: str = "",
    ref: Optional[Guide] = None,
) -> Dict[str, Any]:
    """Grounded report built from the reference procedure.

    Used as the fine-tuning target and as the fallback when the model output is
    unusable, so every sealed report is traceable to a real procedure.
    """
    comp = classify_issue(asset_type, issue, error_code)
    qa_checks = list(comp.qa_checks)
    if ref is not None and ref.source == "MechanicDB":
        fault_code = ref.fault_code
        diagnosis = f"{ref.title}. {ref.description}" if ref.description else ref.title
        steps = [s for s in ref.steps]
        parts = ref.parts or ["Diagnostic time / scan tool"]
        minutes = ref.est_minutes or 60
        label = ref.subject
        qa_checks = [
            f"{ref.fault_code} does not return after a full drive cycle",
            "OBD-II readiness monitors complete with no pending codes",
            "Post-repair scan report attached to the record",
        ]
    else:
        if ref is not None and ref.component != comp.key and comp.key == "general":
            comp = component_by_key(asset_type, ref.component)
        code = (error_code or "").strip().upper()
        fault_code = code or comp.fault_code
        meaning = ""
        if asset_type == "appliance" and code in APPLIANCE_ERROR_CODES:
            meaning = APPLIANCE_ERROR_CODES[code][1] + ". "
        label = comp.label.lower()
        diagnosis = f"{meaning}{comp.label} fault on {device}: {issue.rstrip('.')}."
        if ref is not None:
            diagnosis += f" Repair follows '{ref.title}'."
        steps = [comp.check] + (condensed_steps(ref, limit=4) if ref else [])
        steps.append("Reassemble, power on and run the QA checks before sealing the record.")
        parts = (ref.parts if ref else []) or [comp.label]
        minutes = (ref.est_minutes if ref else 0) or 45
    return {
        "fault_code": fault_code,
        "diagnosis": collapse_runaway_text(diagnosis, max_len=300),
        "severity": comp.severity,
        "parts": parts[:5],
        "repair_steps": steps[:6],
        "qa_checks": qa_checks,
        "estimated_minutes": int(minutes),
        "confidence": 0.85 if ref is not None else 0.6,
        "buyer_advice": BUYER_ADVICE[asset_type].format(label=label),
    }


KNOWN_CODES = {c.fault_code for comps in COMPONENTS.values() for c in comps}


def merge_with_reference(
    parsed: Optional[Dict[str, Any]], grounded: Dict[str, Any], locked: tuple = ()
) -> Dict[str, Any]:
    """Keep the model's fields when they are sane; fall back to the grounded report per field.

    The fault code stays deterministic (OBD-II / display code, else issue + matched manual component);
    the model may only refine a general (*-GEN) code to a specific taxonomy code. `locked` keys always
    come from the grounded report.
    """
    out = dict(grounded)
    if not parsed:
        out["confidence"] = min(out["confidence"], 0.6)
        return out
    model_code = str(parsed.get("fault_code") or "").strip().upper()
    specific = not out["fault_code"].endswith("-GEN")
    if not specific and model_code in KNOWN_CODES:
        out["fault_code"] = model_code
    for key in ("diagnosis", "buyer_advice"):
        val = str(parsed.get(key) or "").strip()
        if specific:
            val = re.sub(r"^General (?:vehicle|phone|appliance) fault on [^:]+:\s*", "", val)
        if len(val) >= 3 and not is_runaway_text(val) and key not in locked:
            out[key] = collapse_runaway_text(val, max_len=300)
    sev = str(parsed.get("severity", "")).lower()
    if sev in {"low", "medium", "high"}:
        out["severity"] = sev
    for key in ("parts", "repair_steps", "qa_checks"):
        if key in locked:
            continue
        vals = parsed.get(key)
        if isinstance(vals, list):
            clean = [collapse_runaway_text(str(v), 220) for v in vals if str(v).strip()]
            clean = [v for v in dict.fromkeys(clean) if not is_runaway_text(v)]
            if len(clean) >= (2 if key == "repair_steps" else 1):
                out[key] = clean[:6]
    try:
        out["estimated_minutes"] = max(5, min(600, int(float(parsed.get("estimated_minutes")))))
    except (TypeError, ValueError):
        pass
    try:
        out["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence"))))
    except (TypeError, ValueError):
        pass
    return out


def training_text(
    asset_type: str, device: str, issue: str, error_code: str, notes: str, ref: Optional[Guide]
) -> str:
    target = reference_report(asset_type, device, issue, error_code, ref)
    return build_prompt(asset_type, device, issue, error_code, notes, ref) + json.dumps(target)


class MultiDomainEngine:
    """Mistral-7B-Instruct (4-bit MLX) + multi-domain LoRA adapter."""

    def __init__(self, model: str = DEFAULT_MODEL, adapter_path: Optional[Path] = None):
        from mlx_lm import generate, load
        from mlx_lm.sample_utils import make_logits_processors, make_sampler

        self._generate = generate
        self._processors = make_logits_processors(repetition_penalty=1.1, repetition_context_size=64)
        self._sampler = make_sampler(temp=0.0)
        adapter = Path(adapter_path) if adapter_path else DEFAULT_ADAPTER
        weights = adapter / "adapters.safetensors"
        if weights.exists():
            self.model, self.tokenizer = load(model, adapter_path=str(adapter))
            self.adapter_hash = hashlib.sha256(weights.read_bytes()).hexdigest()
            self.model_version = "multidomain-mlx-lora-v1"
        else:
            self.model, self.tokenizer = load(model)
            self.adapter_hash = ""
            self.model_version = "mistral-7b-instruct-base"
        self.model_name = f"mlx-lora:{HF_MODEL_ID}"
        self.dataset_merkle_root = ""
        manifest = ROOT / "artifacts" / "dataset_manifest_multidomain.json"
        if manifest.exists():
            self.dataset_merkle_root = json.loads(manifest.read_text()).get("dataset_merkle_root", "")

    def diagnose_asset(
        self,
        asset_type: str,
        device: str,
        issue: str,
        error_code: str = "",
        notes: str = "",
        ref: Optional[Guide] = None,
        max_new_tokens: int = 420,
    ) -> RepairReport:
        prompt = build_prompt(asset_type, device, issue, error_code, notes, ref) + "{"
        text = self._generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_new_tokens,
            verbose=False,
            sampler=self._sampler,
            logits_processors=self._processors,
        )
        parsed = parse_repair_json("{" + text if not text.lstrip().startswith("{") else text)
        grounded = reference_report(asset_type, device, issue, error_code, ref)
        # OBD-II QA criteria are code-specific; keep them from the reference.
        locked = ("qa_checks",) if ref is not None and ref.source == "MechanicDB" else ()
        return RepairReport.from_dict(merge_with_reference(parsed, grounded, locked))
