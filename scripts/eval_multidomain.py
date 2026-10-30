"""Evaluate the multi-domain adapter on the held-out test split (raw model output, no fallback).

Run: python scripts/eval_multidomain.py --limit 30 [--base]
Writes artifacts/eval_metrics_multidomain[_base].json
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.infer import parse_repair_json  # noqa: E402
from src.llm.multidomain import DEFAULT_ADAPTER, MultiDomainEngine  # noqa: E402

REQUIRED = ("fault_code", "diagnosis", "severity", "parts", "repair_steps", "qa_checks")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--base", action="store_true", help="evaluate Mistral-7B without the adapter")
    args = ap.parse_args()

    rows = [json.loads(l) for l in (ROOT / "data/mlx_multidomain/test.jsonl").read_text().splitlines() if l.strip()]
    by_type = collections.defaultdict(list)
    for r in rows:
        by_type[re.search(r"Asset type: (\w+)", r["prompt"]).group(1)].append(r)
    per_type = max(1, args.limit // len(by_type))
    sample = [r for t in sorted(by_type) for r in by_type[t][:per_type]]

    eng = MultiDomainEngine(adapter_path=Path("/nonexistent") if args.base else DEFAULT_ADAPTER)
    stats = collections.defaultdict(lambda: collections.Counter())
    started = time.time()
    for i, r in enumerate(sample, 1):
        asset_type = re.search(r"Asset type: (\w+)", r["prompt"]).group(1)
        target = json.loads(r["completion"])
        text = eng._generate(eng.model, eng.tokenizer, prompt=r["prompt"] + "{", max_tokens=420,
                             verbose=False, sampler=eng._sampler, logits_processors=eng._processors)
        parsed = parse_repair_json("{" + text) or {}
        s = stats[asset_type]
        s["n"] += 1
        s["json_valid"] += int(bool(parsed))
        s["all_keys"] += int(all(k in parsed for k in REQUIRED))
        s["fault_code_exact"] += int(str(parsed.get("fault_code", "")).strip().upper() == target["fault_code"].upper())
        s["severity_match"] += int(str(parsed.get("severity", "")).lower() == target["severity"])
        steps = parsed.get("repair_steps") if isinstance(parsed.get("repair_steps"), list) else []
        s["steps_3_to_6"] += int(3 <= len(steps) <= 6)
        print(f"[{i}/{len(sample)}] {asset_type:<9} target={target['fault_code']:<9} got={parsed.get('fault_code')}")

    def pct(c, k):
        return round(100.0 * c[k] / c["n"], 1) if c["n"] else 0.0

    total = sum(stats.values(), collections.Counter())
    report = {
        "model": "mistral-7b-instruct-4bit" + ("" if args.base else " + multidomain LoRA"),
        "test_examples": total["n"],
        "seconds_per_example": round((time.time() - started) / max(1, total["n"]), 1),
        "overall": {k: pct(total, k) for k in ("json_valid", "all_keys", "fault_code_exact", "severity_match", "steps_3_to_6")},
        "by_type": {t: {"n": c["n"], **{k: pct(c, k) for k in ("json_valid", "fault_code_exact", "severity_match")}}
                    for t, c in sorted(stats.items())},
    }
    out = ROOT / f"artifacts/eval_metrics_multidomain{'_base' if args.base else ''}.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
