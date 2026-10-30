#!/usr/bin/env python3
"""Reproduce the worked Merkle example reported in the paper.

Loads real Proof-of-Repair leaves from the project registry, rebuilds the batch
with the production MerkleTree code, prints every internal node and the root,
emits one membership proof, and then re-runs the same verification after a
single committed field is altered.

Usage:
    python scripts/merkle_worked_example.py [--batch-size 4]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blockchain.merkle import MerkleTree, _pair_hash  # noqa: E402
from src.por.proof import ProofOfRepair  # noqa: E402

FIELDS = set(ProofOfRepair.__dataclass_fields__)

REGISTRY = ROOT / "artifacts" / "por_registry.sqlite3"
SHORT = 12  # hex characters shown for each digest in the report tables


def short(hex_digest: str) -> str:
    return hex_digest[:SHORT] + "…"


def load_proofs(limit: int) -> list[ProofOfRepair]:
    conn = sqlite3.connect(REGISTRY)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT proof_json FROM proofs ORDER BY timestamp LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    out: list[ProofOfRepair] = []
    for r in rows:
        data = json.loads(r["proof_json"])
        out.append(ProofOfRepair.from_dict(data))
    return out


def build(proofs: list[ProofOfRepair]) -> MerkleTree:
    return MerkleTree([bytes.fromhex(p.leaf_digest) for p in proofs])


def print_leaf_table(proofs: list[ProofOfRepair]) -> None:
    print("\n--- committed leaves ---")
    for i, p in enumerate(proofs):
        print(
            f"L{i}  {p.vin}  {p.odometer_km:>7} km  "
            f"{p.report.get('fault_code','?'):<6} "
            f"report={short(p.report_hash)}  cid={short(p.evidence_cid)}"
        )
        print(f"     leaf digest = {p.leaf_digest}")


def print_tree(tree: MerkleTree) -> None:
    print("\n--- tree levels (bottom-up) ---")
    for depth, level in enumerate(tree.levels):
        label = "leaves" if depth == 0 else ("root" if depth == len(tree.levels) - 1 else f"level {depth}")
        for i, node in enumerate(level):
            print(f"{label:<8} [{i}] {node.hex()}")
    print(f"\nroot = {tree.root_hex}")


def print_proof(tree: MerkleTree, proofs: list[ProofOfRepair], index: int) -> None:
    proof = tree.get_proof(index)
    print(f"\n--- membership proof for L{index} ({proofs[index].vin}) ---")
    print(f"leaf      = {proof.leaf_hash_hex}")
    for step, sib in enumerate(proof.siblings):
        side = "right" if (index >> step) % 2 == 0 else "left"
        print(f"sibling {step} ({side:<5}) = {sib}")
    print(f"claimed root = {proof.root_hex}")
    print(f"verify_proof -> {MerkleTree.verify_proof(proof)}")
    print(f"proof size   = {len(proof.siblings)} sibling digests "
          f"({len(proof.siblings) * 32} bytes) for a batch of {len(tree.leaves)}")


def print_tamper(tree: MerkleTree, proofs: list[ProofOfRepair], index: int, new_odometer: int) -> None:
    original = proofs[index]
    proof = tree.get_proof(index)
    print(f"\n--- tamper test: L{index} odometer {original.odometer_km} -> {new_odometer} ---")

    forged = replace(original, usage_value=new_odometer, leaf_digest="")
    forged_leaf = forged.compute_leaf_digest()
    print(f"original leaf = {original.leaf_digest}")
    print(f"forged leaf   = {forged_leaf}")

    print(f"old proof with forged leaf -> "
          f"{MerkleTree.verify_proof(proof, bytes.fromhex(forged_leaf))}")

    rebuilt = build([forged if i == index else p for i, p in enumerate(proofs)])
    print(f"anchored root = {tree.root_hex}")
    print(f"recomputed    = {rebuilt.root_hex}")
    print(f"roots match   -> {rebuilt.root_hex == tree.root_hex}")

    # Show the cascade: which internal nodes changed on the path to the root.
    print("changed nodes on the path:")
    for depth, (before, after) in enumerate(zip(tree.levels, rebuilt.levels)):
        for i, (b, a) in enumerate(zip(before, after)):
            if b != a:
                print(f"  level {depth} [{i}] {short(b.hex())} -> {short(a.hex())}")


def print_odd_rule(proofs: list[ProofOfRepair]) -> None:
    odd = proofs[:3]
    tree = build(odd)
    last = bytes.fromhex(odd[-1].leaf_digest)
    print("\n--- odd-level rule check (3 leaves) ---")
    print(f"node [1] of level 1 = {tree.levels[1][1].hex()}")
    print(f"H(0x01||L2||L2)     = {_pair_hash(last, last).hex()}")
    print(f"last node paired with itself -> {tree.levels[1][1] == _pair_hash(last, last)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--proof-index", type=int, default=3)
    ap.add_argument("--forged-odometer", type=int, default=76000)
    args = ap.parse_args()

    proofs = load_proofs(args.batch_size)
    if len(proofs) < args.batch_size:
        raise SystemExit(f"registry holds only {len(proofs)} proofs")

    tree = build(proofs)
    print_leaf_table(proofs)
    print_tree(tree)
    print_proof(tree, proofs, args.proof_index)
    print_tamper(tree, proofs, args.proof_index, args.forged_odometer)
    print_odd_rule(proofs)


if __name__ == "__main__":
    main()
