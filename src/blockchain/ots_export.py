"""Write the file pair that https://opentimestamps.org needs to verify a batch's Bitcoin timestamp.

<date>_<batch>.bin      the exact bytes whose SHA-256 is the Merkle root
<date>_<batch>.bin.ots  the OpenTimestamps receipt for that root
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.blockchain.merkle import MerkleTree
from src.por.proof import ProofOfRepair, canonical_dumps


def root_preimage(leaves: List[str], proof_for_leaf: Callable[[str], Dict[str, Any]]) -> bytes:
    """Bytes whose SHA-256 is the Merkle root: node = H(0x01|L|R), single leaf = H(0x00|payload)."""
    if len(leaves) == 1:
        por = ProofOfRepair.from_dict(proof_for_leaf(leaves[0]))
        return b"\x00" + canonical_dumps(por.payload_for_leaf()).encode("utf-8")
    below = MerkleTree([bytes.fromhex(h) for h in leaves]).levels[-2]
    return b"\x01" + below[0] + (below[1] if len(below) > 1 else below[0])


def export_batch(
    out_dir: Path,
    batch_id: str,
    merkle_root: str,
    receipt_path: Optional[str],
    leaves: List[str],
    when: datetime,
    proof_for_leaf: Callable[[str], Dict[str, Any]],
) -> Optional[Path]:
    """Return the .bin path written, or None when there is no receipt or the data does not hash to the root."""
    receipt = Path(receipt_path) if receipt_path else None
    if not leaves or receipt is None or not receipt.exists():
        return None
    data = root_preimage(leaves, proof_for_leaf)
    if hashlib.sha256(data).hexdigest() != merkle_root:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{when:%Y-%m-%d_%H%M}_{batch_id}"
    (out_dir / f"{name}.bin").write_bytes(data)
    shutil.copyfile(receipt, out_dir / f"{name}.bin.ots")
    return out_dir / f"{name}.bin"
