"""VG key parser — pure regex, no external dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# VG:{NAME}-{SUFFIX}:{TIER}-{PRIMARY}·{12×class_code+digit}
_VG_PATTERN = re.compile(
    r"VG:([A-Z0-9]+-[A-Z0-9]+):(V[0-6])-([A-Z]{4})"
    r"\xb7"  # middle dot
    r"((?:[A-Z][a-z]\d){12})"
)

_SCORE_PATTERN = re.compile(r"([A-Z][a-z])(\d)")

CLASS_CODES = {
    "Se": "Sentinel",
    "Op": "Operative",
    "An": "Analyst",
    "Ar": "Architect",
    "Co": "Conduit",
    "Ad": "Adaptor",
    "St": "Steward",
    "Sc": "Scout",
    "Sa": "Sage",
    "So": "Sovereign",
    "Br": "Broker",
    "Fo": "Forge",
}


@dataclass
class VGKey:
    """Parsed Verigent key."""

    handle: str
    tier: int  # 0-6
    primary: str  # 4-letter class code e.g. ARCH
    scores: dict[str, int] = field(default_factory=dict)  # code -> 0-9
    raw: str = ""

    @property
    def tier_label(self) -> str:
        return f"V{self.tier}"

    def score_for(self, class_code: str) -> int:
        """Get score (0-9) for a 2-letter class code."""
        return self.scores.get(class_code, 0)

    def score_percent(self, class_code: str) -> int:
        """Get score as rough percentage (digit * 10)."""
        return self.score_for(class_code) * 10


def parse_vg_key(raw: str) -> Optional[VGKey]:
    """Parse a VG key string. Returns None if invalid."""
    m = _VG_PATTERN.search(raw)
    if not m:
        return None

    handle = m.group(1)
    tier = int(m.group(2)[1])
    primary = m.group(3)
    radar = m.group(4)

    scores: dict[str, int] = {}
    for sm in _SCORE_PATTERN.finditer(radar):
        code, digit = sm.group(1), int(sm.group(2))
        if code in CLASS_CODES:
            scores[code] = digit

    if len(scores) != 12:
        return None

    return VGKey(handle=handle, tier=tier, primary=primary, scores=scores, raw=raw)


def extract_vg_key(
    *,
    system_prompt: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
    metadata: Optional[dict] = None,
) -> Optional[VGKey]:
    """Extract a VG key from common agent sources.

    Checks (in order):
    1. System prompt text (searches for VG: prefix)
    2. HTTP headers (X-Verigent header)
    3. JSON metadata (x-verigent field)
    """
    sources = []

    if system_prompt:
        sources.append(system_prompt)

    if headers:
        vg_header = headers.get("X-Verigent") or headers.get("x-verigent")
        if vg_header:
            sources.append(vg_header)

    if metadata:
        vg_meta = metadata.get("x-verigent") or metadata.get("X-Verigent")
        if vg_meta:
            sources.append(str(vg_meta))

    for source in sources:
        key = parse_vg_key(source)
        if key:
            return key

    return None
