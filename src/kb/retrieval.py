"""Pick the reference procedure that grounds a diagnosis.

Rule: a car with an OBD-II code uses the MechanicDB entry for that code;
otherwise the issue text selects a component and the best device match among
guides for that component wins. Same logic in memory (offline / training) and
in PostgreSQL (live API, full-text search over repair_guides).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.kb.catalog import Guide, classify_issue, extract_dtc

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "and", "of", "for", "with", "to", "in", "on", "replacement", "repair"}


def tokens(text: str) -> List[str]:
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP]


def _device_score(device_tokens: Iterable[str], guide: Guide) -> float:
    hay = set(tokens(f"{guide.device} {guide.title} {guide.family}"))
    toks = list(device_tokens)
    if not toks:
        return 0.0
    hits = sum(1.0 + (0.5 if any(c.isdigit() for c in t) else 0.0) for t in toks if t in hay)
    return hits / len(toks)


class MemoryRetriever:
    def __init__(self, guides: List[Guide]):
        self.guides = guides
        self.by_dtc: Dict[str, Guide] = {
            g.fault_code: g for g in guides if g.source == "MechanicDB"
        }

    @classmethod
    def from_jsonl(cls, path: Path) -> "MemoryRetriever":
        rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
        return cls([Guide.from_dict(r) for r in rows])

    def best(self, asset_type: str, device: str, issue: str, error_code: str = "") -> Optional[Guide]:
        if asset_type == "car":
            dtc = extract_dtc(error_code) or extract_dtc(issue)
            if dtc in self.by_dtc:
                return self.by_dtc[dtc]
        comp = classify_issue(asset_type, issue, error_code)
        pool = [g for g in self.guides if g.asset_type == asset_type and g.source != "MechanicDB"]
        same = [g for g in pool if g.component == comp.key]
        pool = same or pool
        if not pool:
            return None
        dev = tokens(device)
        issue_toks = set(tokens(issue))
        return max(
            pool,
            key=lambda g: (
                _device_score(dev, g),
                -len(g.device),
                -len(g.subject),
                len(issue_toks & set(tokens(f"{g.title} {g.subject}"))),
                -len(g.steps),
            ),
        )
