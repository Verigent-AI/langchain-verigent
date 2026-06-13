"""Trust evaluation logic for Verigent keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .parser import CLASS_CODES, VGKey


@dataclass
class TrustScore:
    """Computed trust evaluation for a VG key."""

    key: VGKey
    composite: float  # 0.0 - 1.0
    tier_weight: float
    primary_score: float
    meets_threshold: bool

    @property
    def percent(self) -> int:
        return int(self.composite * 100)


# Tier weights: higher tier = more trust baseline
_TIER_WEIGHTS = {0: 0.1, 1: 0.25, 2: 0.4, 3: 0.55, 4: 0.7, 5: 0.85, 6: 1.0}


def evaluate_trust(
    key: VGKey,
    *,
    required_classes: Optional[list[str]] = None,
    min_tier: int = 0,
    threshold: float = 0.5,
) -> TrustScore:
    """Evaluate trust from a parsed VG key.

    Args:
        key: Parsed VGKey instance.
        required_classes: 2-letter class codes the agent must score on.
            If provided, composite is weighted toward these classes.
        min_tier: Minimum tier required (0-6). Below this = automatic fail.
        threshold: Minimum composite score to pass (0.0-1.0).

    Returns:
        TrustScore with composite and pass/fail.
    """
    tier_weight = _TIER_WEIGHTS.get(key.tier, 0.0)

    # If below minimum tier, automatic fail
    if key.tier < min_tier:
        return TrustScore(
            key=key,
            composite=tier_weight * 0.5,
            tier_weight=tier_weight,
            primary_score=0.0,
            meets_threshold=False,
        )

    # Calculate class-based score
    if required_classes:
        # Weight toward required classes
        relevant_scores = [key.score_for(c) / 9.0 for c in required_classes]
        class_score = sum(relevant_scores) / len(relevant_scores) if relevant_scores else 0.0
    else:
        # Use all 12 scores averaged
        all_scores = [v / 9.0 for v in key.scores.values()]
        class_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Primary class gets a bonus
    primary_code = _primary_to_code(key.primary)
    primary_score = key.score_for(primary_code) / 9.0 if primary_code else class_score

    # Composite: 40% tier, 40% class scores, 20% primary
    composite = (tier_weight * 0.4) + (class_score * 0.4) + (primary_score * 0.2)

    return TrustScore(
        key=key,
        composite=composite,
        tier_weight=tier_weight,
        primary_score=primary_score,
        meets_threshold=composite >= threshold,
    )


def _primary_to_code(primary: str) -> Optional[str]:
    """Map 4-letter primary (e.g. ARCH) to 2-letter code (e.g. Ar)."""
    primary_lower = primary.lower()
    for code, name in CLASS_CODES.items():
        if name.lower().startswith(primary_lower[:4]):
            return code
    return None
