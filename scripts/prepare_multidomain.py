"""Build the multi-domain repair knowledge base and the MLX fine-tuning split.

Outputs
  data/processed/repair_kb.jsonl          every guide / DTC entry (loaded into PostgreSQL)
  data/mlx_multidomain/{train,valid,test}.jsonl
  artifacts/dataset_manifest_multidomain.json   counts + Merkle root of the training set

Run: python scripts/prepare_multidomain.py [--kb-only]
"""

from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blockchain.merkle import merkle_root_from_payloads  # noqa: E402
from src.kb.catalog import (  # noqa: E402
    APPLIANCE_ERROR_CODES,
    component_by_key,
    extract_dtc,
    load_mechanicdb,
    load_myfixit,
)
from src.kb.retrieval import MemoryRetriever  # noqa: E402
from src.llm.multidomain import training_text  # noqa: E402

SEED = 42
CAP = {"phone": 700, "appliance": 450, "car": 220}
CARS = ["2016 Honda Civic", "2015 Toyota Camry", "2018 Ford F-150", "2014 BMW 3-Series",
        "2016 Chevrolet Malibu", "2017 Hyundai Elantra", "2019 Maruti Suzuki Swift"]
NOTES = ["none", "customer dropped the device last week", "intermittent for two weeks",
         "second-hand unit, no service history", "issue started after a software update"]


def main() -> None:
    rng = random.Random(SEED)
    guides = load_myfixit(ROOT / "data/raw/MyFixit")
    dtcs = load_mechanicdb(ROOT / "data/raw/MechanicDB")
    kb = guides + dtcs

    out_kb = ROOT / "data/processed/repair_kb.jsonl"
    out_kb.parent.mkdir(parents=True, exist_ok=True)
    with out_kb.open("w", encoding="utf-8") as f:
        for g in kb:
            f.write(json.dumps(g.to_dict()) + "\n")
    if "--kb-only" in sys.argv:
        print(f"wrote {len(kb)} entries to {out_kb} (training split untouched)")
        return

    retriever = MemoryRetriever(kb)
    examples = []  # (split_key, text)

    # 1) iFixit guides: one owner complaint per guide, grounded on that guide.
    by_type = collections.defaultdict(list)
    for g in guides:
        by_type[g.asset_type].append(g)
    for asset_type, pool in by_type.items():
        tagged = [g for g in pool if g.component != "general"]
        rng.shuffle(tagged)
        for g in tagged[: CAP[asset_type]]:
            comp = component_by_key(asset_type, g.component)
            issue = rng.choice(comp.symptoms)
            code = ""
            if asset_type == "appliance":
                codes = [c for c, (k, _) in APPLIANCE_ERROR_CODES.items() if k == g.component]
                if codes and rng.random() < 0.35:
                    code = rng.choice(codes)
            text = training_text(asset_type, g.device, issue, code, rng.choice(NOTES), g)
            examples.append((g.ref_id, text))

    # 2) OBD-II codes: grounded on MechanicDB fixes for that code.
    for d in dtcs:
        for variant in range(3):
            car = rng.choice(CARS)
            issue = [
                f"Check engine light is on and the scan tool reports {d.fault_code} ({d.subject}).",
                f"Warning light on the dashboard; stored code {d.fault_code}.",
                f"Customer reports {d.subject.lower()} symptoms; code {d.fault_code} is stored.",
            ][variant]
            text = training_text("car", car, issue, d.fault_code, rng.choice(NOTES[:3]), d)
            examples.append((f"{d.ref_id}-{variant}", text))

    # 3) Real owner complaints (NHTSA) from the vehicle dataset, grounded by retrieval.
    vehicle_rows = [json.loads(l) for l in (ROOT / "data/processed/train_raw.jsonl").read_text().splitlines() if l.strip()]
    nhtsa = [r for r in vehicle_rows if r.get("source") == "nhtsa_complaints"]
    rng.shuffle(nhtsa)
    for r in nhtsa[:150]:
        complaint = r["input"].split("Complaint:", 1)[-1].strip()[:280]
        dtc = extract_dtc(complaint)
        ref = retriever.best("car", r.get("vehicle", ""), complaint, dtc)
        text = training_text("car", r.get("vehicle", "used car"), complaint, dtc, "none", ref)
        examples.append((r["id"], text))

    # Split by source item so no guide appears in more than one split.
    keys = sorted({k for k, _ in examples})
    rng.shuffle(keys)
    n = len(keys)
    valid_keys = set(keys[: max(40, n // 25)])
    test_keys = set(keys[len(valid_keys): len(valid_keys) + max(40, n // 25)])
    splits = {"train": [], "valid": [], "test": []}
    for k, text in examples:
        split = "valid" if k in valid_keys else "test" if k in test_keys else "train"
        prompt, completion = text.split("### Assistant\n", 1)
        splits[split].append({"prompt": prompt + "### Assistant\n", "completion": completion})

    out_dir = ROOT / "data/mlx_multidomain"
    out_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in splits.items():
        rng.shuffle(rows)
        with (out_dir / f"{split}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    root_hex, _ = merkle_root_from_payloads(
        (r["prompt"] + r["completion"]).encode("utf-8") for r in splits["train"]
    )
    manifest = {
        "domain": "phones_cars_appliances_proof_of_repair",
        "seed": SEED,
        "knowledge_base": {
            "total": len(kb),
            "by_type": dict(collections.Counter(g.asset_type for g in kb)),
            "by_source": dict(collections.Counter(g.source for g in kb)),
        },
        "train": len(splits["train"]),
        "valid": len(splits["valid"]),
        "test": len(splits["test"]),
        "dataset_merkle_root": root_hex,
        "datasets": ["MyFixit (iFixit) Phone/Appliance/Car and Truck", "MechanicDB OBD-II", "NHTSA complaints"],
    }
    (ROOT / "artifacts/dataset_manifest_multidomain.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
