"""Deterministic Merkle tree for Proof-of-Repair leaf digests.

Follows RSP / OpenTimestamps style binary Merkle trees (P4, P8).

Why a Merkle tree?
    Writing every repair record to the blockchain would cost one transaction per
    record. Instead we collect a batch of records, hash them into a tree, and put
    only the single 32-byte ROOT on-chain. Later, anyone can prove that one record
    was in the batch using a short "Merkle proof" (about log2(N) hashes), without
    seeing any of the other records.

Example with 4 records (leaves L0..L3):

                    ROOT = H(0x01 || N01 || N23)
                   /                            \\
        N01 = H(0x01 || L0 || L1)      N23 = H(0x01 || L2 || L3)
          /          \\                    /          \\
        L0            L1                L2            L3

    To prove L2 is in the tree we only need its siblings: [L3, N01].
    Verifier computes H(L2, L3) -> N23, then H(N01, N23) -> ROOT, and compares
    with the root stored on the blockchain.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


def sha256_hex(data: bytes) -> str:
    # SHA-256 as a 64-character hex string (human readable).
    return hashlib.sha256(data).hexdigest()


def sha256_bytes(data: bytes) -> bytes:
    # SHA-256 as raw 32 bytes (what the tree works with internally).
    return hashlib.sha256(data).digest()


# Domain separation: leaves are hashed with a 0x00 prefix and internal nodes with
# a 0x01 prefix. Without this, an attacker could present an internal node as if
# it were a leaf (a "second-preimage" attack). The prefix makes the two kinds of
# hash impossible to confuse. The same rule is used by Certificate Transparency
# (RFC 6962).

def _pair_hash(left: bytes, right: bytes) -> bytes:
    # Domain-separated node hash: H(0x01 || left || right)
    # Order matters: H(a, b) != H(b, a), so the verifier must know which side
    # each sibling is on (that is what the leaf index tells it).
    return sha256_bytes(b"\x01" + left + right)


def leaf_hash(payload: bytes) -> bytes:
    # Domain-separated leaf hash: H(0x00 || payload)
    return sha256_bytes(b"\x00" + payload)


@dataclass(frozen=True)
class MerkleProof:
    """Everything a buyer needs to prove one record is inside an anchored batch."""

    leaf_index: int  # position of the record in the batch (tells left/right at each level)
    leaf_hash_hex: str  # the record's leaf digest
    siblings: Tuple[str, ...]  # hex hashes from leaf toward root
    root_hex: str  # the root that was written to the blockchain


class MerkleTree:
    """Binary Merkle tree over an ordered list of pre-hashed leaves (32-byte digests)."""

    def __init__(self, leaves: Sequence[bytes]):
        if not leaves:
            raise ValueError("MerkleTree requires at least one leaf")
        self.leaves: List[bytes] = [bytes(x) for x in leaves]
        # levels[0] = leaves, levels[1] = their parents, ..., levels[-1] = [root]
        self.levels: List[List[bytes]] = self._build(self.leaves)

    @staticmethod
    def _build(leaves: List[bytes]) -> List[List[bytes]]:
        """Build the tree bottom-up, one level at a time, until one hash (the root) is left."""
        levels: List[List[bytes]] = [list(leaves)]
        current = list(leaves)
        while len(current) > 1:
            nxt: List[bytes] = []
            # Walk the level two nodes at a time and hash each pair into a parent.
            for i in range(0, len(current), 2):
                left = current[i]
                # Odd number of nodes: the last one is paired with itself
                # (same approach as Bitcoin), so every level halves cleanly.
                right = current[i + 1] if i + 1 < len(current) else current[i]
                nxt.append(_pair_hash(left, right))
            levels.append(nxt)
            current = nxt
        return levels

    @property
    def root(self) -> bytes:
        # The top level has exactly one node: the Merkle root.
        return self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        # Hex form of the root; this is the value anchored on Ethereum / Bitcoin.
        return self.root.hex()

    def get_proof(self, index: int) -> MerkleProof:
        """Collect the sibling hash at every level on the path from leaf `index` to the root."""
        if index < 0 or index >= len(self.leaves):
            raise IndexError("leaf index out of range")
        siblings: List[str] = []
        idx = index
        for level in self.levels[:-1]:  # every level except the root itself
            if idx % 2 == 0:
                # We are a LEFT child, so our sibling is on the right
                # (or ourselves, if we were the odd node duplicated in _build).
                sibling_idx = idx + 1 if idx + 1 < len(level) else idx
            else:
                # We are a RIGHT child, so our sibling is on the left.
                sibling_idx = idx - 1
            siblings.append(level[sibling_idx].hex())
            idx //= 2  # move up: our parent's position in the next level
        return MerkleProof(
            leaf_index=index,
            leaf_hash_hex=self.leaves[index].hex(),
            siblings=tuple(siblings),
            root_hex=self.root_hex,
        )

    @staticmethod
    def verify_proof(proof: MerkleProof, leaf_digest: Optional[bytes] = None) -> bool:
        """Recompute the root from the leaf + siblings and check it matches proof.root_hex.

        This needs no access to the other records or to the tree: only the proof.
        If even one bit of the leaf or any sibling is changed, the recomputed root
        will be different and verification fails.
        """
        current = leaf_digest if leaf_digest is not None else bytes.fromhex(proof.leaf_hash_hex)
        # The leaf we were given must be the leaf the proof was made for.
        if current.hex() != proof.leaf_hash_hex:
            return False
        idx = proof.leaf_index
        for sib_hex in proof.siblings:
            sibling = bytes.fromhex(sib_hex)
            # Even index -> we are on the left, odd index -> we are on the right.
            if idx % 2 == 0:
                current = _pair_hash(current, sibling)
            else:
                current = _pair_hash(sibling, current)
            idx //= 2
        # After climbing every level we should land exactly on the anchored root.
        return current.hex() == proof.root_hex


def merkle_root_from_payloads(payloads: Iterable[bytes]) -> Tuple[str, MerkleTree]:
    """Convenience helper: hash raw payloads into leaves, build the tree, return (root, tree)."""
    leaves = [leaf_hash(p) for p in payloads]
    tree = MerkleTree(leaves)
    return tree.root_hex, tree
