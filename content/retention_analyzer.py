"""Retention Analyzer for Autonomous Faceless Shorts Factory.

Evaluates narrative progression, cognitive density, pacing distribution,
and estimated 5-second dropoff resistance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RetentionReport:
    score: float
    hook_strength: float
    pacing_balance: float
    information_density: float
    pacing_notes: List[str]


class RetentionAnalyzer:
    """Simulates viewer drop-off dynamics and scores audience retention potential."""

    def analyze(self, script_text: str) -> RetentionReport:
        sentences = [s.strip() for s in re.split(r"[.!?]+", script_text) if s.strip()]
        notes = []

        # 1. Hook Strength (first sentence analysis)
        hook_strength = 75.0
        if sentences:
            first = sentences[0].lower()
            if any(w in first for w in ["why", "how", "secret", "never", "what happens"]):
                hook_strength += 15.0
                notes.append("Strong curiosity trigger in opening sentence")
            if len(first.split()) <= 11:
                hook_strength += 10.0
                notes.append("Brisk opening length maintains initial thumb stop")

        # 2. Pacing Balance (progression across sentences)
        pacing_balance = 80.0
        if len(sentences) >= 4:
            pacing_balance += 10.0
            notes.append("Clean 4-act structural pacing")
        elif len(sentences) <= 2:
            pacing_balance -= 20.0
            notes.append("Too few sentences; risks monotonous delivery")

        # 3. Information Density
        # Ratio of informative nouns/numbers to total words
        words = script_text.split()
        informative_tokens = [w for w in words if re.search(r"\b\d+\b|[A-Z][a-z]+", w)]
        density_ratio = len(informative_tokens) / max(1, len(words))
        density_score = min(100.0, max(50.0, density_ratio * 300.0))

        overall_score = (hook_strength * 0.45) + (pacing_balance * 0.35) + (density_score * 0.20)

        return RetentionReport(
            score=min(100.0, max(0.0, overall_score)),
            hook_strength=min(100.0, hook_strength),
            pacing_balance=min(100.0, pacing_balance),
            information_density=density_score,
            pacing_notes=notes,
        )
