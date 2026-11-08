"""Topic Scoring and Ranking Engine for Autonomous Faceless Shorts Factory.

Evaluates candidates on novelty, curiosity hook strength, visual feasibility,
25-second brevity fit, and deduplication history.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from intelligence.topic_deduplicator import TopicDeduplicator
from intelligence.trend_discovery import TopicCandidate

logger = logging.getLogger("factory.topic_scorer")

HIGH_CURIOSITY_SIGNALS = [
    r"\bwhy\b", r"\bhow\b", r"\bsecret\b", r"\bnever\b", r"\breal reason\b",
    r"\bwhat happens\b", r"\bliterally\b", r"\bhidden\b", r"\bstronger than\b",
    r"\bdissolves\b", r"\bshrinks\b", r"\bbillion\b", r"\bdollar\b", r"\bmillion\b"
]

VISUAL_POTENTIAL_WORDS = [
    r"\bbrain\b", r"\bacid\b", r"\bbone\b", r"\bdoor\b", r"\broom\b", r"\bhoney\b",
    r"\bsneeze\b", r"\bdance\b", r"\bbuttons\b", r"\bwinter\b", r"\bplanet\b",
    r"\bglass\b", r"\bblack hole\b", r"\bjellyfish\b", r"\bmuscle\b", r"\bbank\b",
    r"\bpainting\b", r"\blouvre\b", r"\bwater\b", r"\bfreeze\b", r"\bfire\b"
]


class TopicScorer:
    """Ranks topic candidates according to algorithmic virality and format suitability."""

    def __init__(self, deduplicator: TopicDeduplicator):
        self.deduplicator = deduplicator

    def score_candidate(self, candidate: TopicCandidate) -> float:
        """Compute an overall score between 0.0 and 100.0 for a candidate."""
        # 1. Deduplication Check
        if self.deduplicator.is_duplicate(candidate.title, candidate.summary):
            logger.info("Candidate '%s' rejected by deduplication filter.", candidate.title)
            return 0.0

        score = 50.0  # Base score for valid unique candidate

        # 2. Curiosity & Hook Signals (up to +20 points)
        text_lower = f"{candidate.title} {candidate.summary}".lower()
        curiosity_hits = sum(1 for pat in HIGH_CURIOSITY_SIGNALS if re.search(pat, text_lower))
        score += min(20.0, curiosity_hits * 6.0)

        # 3. Visual Potential (up to +15 points)
        visual_hits = sum(1 for pat in VISUAL_POTENTIAL_WORDS if re.search(pat, text_lower))
        score += min(15.0, visual_hits * 5.0)

        # 4. Length & Brevity Fit (up to +10 points)
        # Optimal summary is 15-40 words for a 25s short
        word_count = len(candidate.summary.split())
        if 15 <= word_count <= 45:
            score += 10.0
        elif word_count < 15:
            score += 5.0
        else:
            score += 2.0  # Too verbose, may need heavy truncation

        # 5. Authoritative Source Credibility (+5 points)
        if any(auth in candidate.source_url.lower() for auth in ["nih.gov", "nasa.gov", "smithsonian", "nature", "pubmed", "louvre", "bbc"]):
            score += 5.0

        return min(100.0, max(0.0, score))

    def rank_candidates(self, candidates: List[TopicCandidate]) -> List[Tuple[TopicCandidate, float]]:
        """Score and sort candidates from highest to lowest score."""
        scored = []
        for c in candidates:
            s = self.score_candidate(c)
            if s > 0.0:  # Exclude duplicates / zero scores
                scored.append((c, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
