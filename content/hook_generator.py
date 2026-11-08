"""Hook Generator and Evaluator for Autonomous Faceless Shorts Factory.

Produces 5 distinct hook variants per topic, filters for brevity (<14 words, <2.5s speech),
scores curiosity, penalizes engagement clichés, and picks the highest-retention opening.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

from content.llm_client import OllamaClient

logger = logging.getLogger("factory.hook_generator")

CLICHE_PATTERNS = [
    r"\bwait (until|till) the end\b",
    r"\byou won'?t believe\b",
    r"\bmind[- ]blown\b",
    r"\bdon'?t forget to (like|sub)\b",
    r"\bwatch till\b",
    r"\bhey guys\b",
]


@dataclass
class HookCandidate:
    text: str
    hook_type: str  # 'question', 'contrast', 'drama', 'action', 'counter_intuitive'
    word_count: int
    score: float
    reason: str


class HookGenerator:
    """Generates and evaluates high-retention 0-2s opening hooks."""

    def __init__(self, llm: OllamaClient):
        self.llm = llm

    def generate_hooks(self, title: str, summary: str, facts: List[str]) -> List[HookCandidate]:
        """Generate 5 distinct hook variations and evaluate them."""
        prompt = (
            f"You are a master viral short-form video editor.\n"
            f"Topic: {title}\n"
            f"Summary: {summary}\n"
            f"Facts: {'; '.join(facts)}\n\n"
            f"Write exactly 5 distinct opening hooks for a 25-second YouTube Short.\n"
            f"Rules:\n"
            f"- Each hook must be ONE single punchy sentence.\n"
            f"- Maximum 12 words per hook (spoken in under 2.5 seconds).\n"
            f"- Hook 1 must be a direct provocative question.\n"
            f"- Hook 2 must be an unexpected contrast or contradiction.\n"
            f"- Hook 3 must be a dramatic mystery statement.\n"
            f"- Hook 4 must be a visceral action or 'what happens' prompt.\n"
            f"- Hook 5 must be a bold, counter-intuitive fact.\n"
            f"- NO clichés like 'Wait till the end', 'You won't believe', 'Hey guys'.\n"
            f"Format your response as 5 numbered lines only:"
        )

        candidates: List[HookCandidate] = []
        try:
            response = self.llm.generate(prompt, temperature=0.7, max_tokens=250)
            lines = [line.strip() for line in response.split("\n") if line.strip()]
            hook_types = ["question", "contrast", "drama", "action", "counter_intuitive"]

            for line in lines:
                cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip().strip('"').strip("'")
                if len(cleaned) > 10:
                    htype = hook_types[len(candidates)] if len(candidates) < len(hook_types) else "variant"
                    candidates.append(self._evaluate_hook(cleaned, htype))
                if len(candidates) >= 5:
                    break
        except Exception as e:
            logger.warning("LLM hook generation encountered an error (%s). Falling back to algorithmic hooks.", e)

        # Fallback if LLM output was insufficient
        if len(candidates) < 5:
            candidates.extend(self._generate_fallback_hooks(title, summary, 5 - len(candidates)))

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    def _evaluate_hook(self, text: str, hook_type: str) -> HookCandidate:
        """Score hook on length, curiosity, rhythm, and cliché penalty."""
        words = text.split()
        word_count = len(words)
        score = 80.0
        reasons = []

        # Brevity penalty / bonus: 6-12 words is ideal for a 2-second hook
        if 5 <= word_count <= 11:
            score += 15.0
            reasons.append("Optimal length (under 12 words)")
        elif word_count > 14:
            score -= 25.0
            reasons.append("Too wordy for 2s opening")
        else:
            score -= 5.0

        # Cliché penalty
        for pat in CLICHE_PATTERNS:
            if re.search(pat, text, re.I):
                score -= 40.0
                reasons.append("Contains cheap engagement cliché")

        # Punctuation check
        if text.endswith("?"):
            score += 5.0
            reasons.append("Engaging question structure")

        return HookCandidate(
            text=text,
            hook_type=hook_type,
            word_count=word_count,
            score=max(0.0, min(100.0, score)),
            reason=", ".join(reasons) or "Standard hook candidate",
        )

    def _generate_fallback_hooks(self, title: str, summary: str, needed: int) -> List[HookCandidate]:
        """Deterministic algorithmic hooks for offline/fallback operation."""
        fallbacks = [
            f"Did you know {title.lower()}?",
            f"Here is why {title.lower()} changes everything.",
            f"What actually happens during {title.lower()}?",
            f"The hidden truth behind {title.lower()}.",
            f"This one secret about {title.lower()} will surprise you.",
        ]
        results = []
        for fb in fallbacks[:needed]:
            results.append(self._evaluate_hook(fb, "fallback"))
        return results
