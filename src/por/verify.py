"""Independent verification of Proof-of-Repair objects (phones, cars, appliances).

This is what a second-hand buyer relies on. It never trusts the stored hashes;
it RECOMPUTES them from the data and compares. There are five checks, each one
covering a different way a record could be faked or edited:

    1. report_hash   - was the AI repair report edited after sealing?
    2. leaf_digest   - was any other field (device ID, km, workshop, time...) edited?
    3. evidence      - is the off-chain evidence file still the original one?
    4. merkle        - is this record really one of the records in an anchored batch?
    5. chain_anchor  - is that batch's Merkle root actually recorded on the blockchain?

Checks 1-3 prove the record is internally consistent; checks 4-5 prove it
existed at anchoring time and that a workshop cannot quietly rewrite it later.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from src.blockchain.merkle import MerkleProof, MerkleTree
from src.cloud.storage import EvidenceStore
from src.por.proof import ProofOfRepair, canonical_dumps, sha256_hex


def verify_report_hash(por: ProofOfRepair) -> bool:
    """Check 1: re-hash the report text and compare with the report_hash sealed in the record.

    Example: someone edits severity "high" -> "low" in the database.
    The recomputed hash changes, so this returns False.
    """
    return sha256_hex(canonical_dumps(por.report)) == por.report_hash


def verify_leaf_digest(por: ProofOfRepair) -> bool:
    """Check 2: recompute the leaf digest from all sealed fields and compare.

    Example: a seller lowers the odometer from 120,000 km to 60,000 km.
    usage_value is part of the leaf payload, so the recomputed digest differs.
    """
    expected = por.leaf_digest
    # Work on a copy (`replace`) so the original object's leaf_digest is not overwritten.
    recomputed = replace(por, leaf_digest="").compute_leaf_digest()
    return expected == recomputed


def verify_evidence(store: EvidenceStore, cid: str) -> bool:
    """Check 3: the evidence file is stored under its own SHA-256 (content addressing).

    The store re-hashes the file and checks the hash still equals its name (the CID).
    A swapped or edited file would have a different hash.
    """
    return store.verify(cid)


def verify_merkle_inclusion(proof_dict: Dict[str, Any], leaf_digest_hex: str) -> bool:
    """Check 4: prove this record's leaf is inside the batch whose root was anchored.

    Uses the sibling hashes stored for this record to climb the tree back up to
    the root (see MerkleTree.verify_proof in src/blockchain/merkle.py).
    """
    proof = MerkleProof(
        leaf_index=int(proof_dict["leaf_index"]),
        leaf_hash_hex=proof_dict["leaf_hash_hex"],
        siblings=tuple(proof_dict["siblings"]),
        root_hex=proof_dict["root_hex"],
    )
    # The Merkle proof must belong to THIS record, not to some other valid record.
    if proof.leaf_hash_hex != leaf_digest_hex:
        return False
    return MerkleTree.verify_proof(proof)


def verify_full(
    por: ProofOfRepair,
    store: Optional[EvidenceStore] = None,
    merkle_proof: Optional[Dict[str, Any]] = None,
    ledger=None,
) -> Dict[str, bool]:
    """Run every check and return a pass/fail result for each, plus an overall all_ok.

    store, merkle_proof and ledger are optional so the function also works offline
    or before a record has been batched. A check whose input is missing is reported
    as True here; the API (/api/verify) sets merkle/chain_anchor to False itself
    when a record has not been anchored yet, so the buyer never sees a false "all OK".
    """
    # Checks 1 and 2 only need the record itself.
    results = {
        "report_hash": verify_report_hash(por),
        "leaf_digest": verify_leaf_digest(por),
        "evidence": True,
        "merkle": True,
        "chain_anchor": True,
    }
    # Check 3: needs access to the evidence store.
    if store is not None:
        results["evidence"] = verify_evidence(store, por.evidence_cid)
    # Check 4: needs the Merkle path saved when the batch was anchored.
    if merkle_proof is not None:
        results["merkle"] = verify_merkle_inclusion(merkle_proof, por.leaf_digest)
        # Check 5: ask the smart contract (isRootAnchored) whether this root is on-chain.
        if ledger is not None:
            results["chain_anchor"] = ledger.is_root_anchored(merkle_proof["root_hex"])
    # The record is trusted only if every single check passed.
    results["all_ok"] = all(results.values())
    return results
