"""Scriptwriter Engine for Autonomous Faceless Shorts Factory.

Generates 22-28 second (45-65 word) scripts with precise narrative pacing:
0-2s Hook -> 2-7s Context -> 7-18s Core Mechanism -> 18-25s Punchline.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from content.llm_client import OllamaClient

logger = logging.getLogger("factory.scriptwriter")


@dataclass
class GeneratedScript:
    hook: str
    body_text: str
    full_script: str
    word_count: int
    estimated_duration_seconds: float


class Scriptwriter:
    """Produces timing-disciplined spoken scripts for vertical short-form video."""

    def __init__(self, llm: OllamaClient, words_per_minute: float = 140.0):
        self.llm = llm
        self.wpm = words_per_minute

    def estimate_duration(self, word_count: int) -> float:
        """Estimate speech duration in seconds given word count."""
        return (word_count / self.wpm) * 60.0

    def generate_script(
        self,
        title: str,
        summary: str,
        niche: str,
        seed_facts: List[str],
        chosen_hook: str,
    ) -> GeneratedScript:
        """Prompt local LLM to draft a 45-65 word script incorporating the hook."""
        prompt = (
            f"You are a professional YouTube Shorts scriptwriter.\n"
            f"Topic: {title}\n"
            f"Niche: {niche}\n"
            f"Core Facts: {'; '.join(seed_facts)}\n"
            f"Chosen Opening Hook: \"{chosen_hook}\"\n\n"
            f"Task: Write the full voiceover script starting exactly with the Chosen Opening Hook.\n"
            f"CRITICAL CONSTRAINTS:\n"
            f"1. Total length MUST be between 48 and 62 spoken words total.\n"
            f"2. Structure:\n"
            f"   - Sentence 1 (0-2s): The hook.\n"
            f"   - Sentence 2 (2-7s): Context and buildup.\n"
            f"   - Sentences 3-4 (7-18s): The core factual mechanism or surprising reveal.\n"
            f"   - Final Sentence (18-25s): A punchy resolution or twist. NO subscribe/like begs!\n"
            f"3. Return ONLY plain spoken English text. No labels like 'Narrator:', no parentheticals, no markdown fences.\n\n"
            f"Script:"
        )

        raw_script = ""
        try:
            raw_script = self.llm.generate(prompt, temperature=0.7, max_tokens=200)
        except Exception as e:
            logger.warning("LLM script generation failed (%s). Using fallback template.", e)

        # Clean any speaker labels, stage directions, or markdown
        cleaned = self._clean_script_text(raw_script, chosen_hook)

        # Verify word count and enforce 45-65 word target
        words = cleaned.split()
        if len(words) < 40 or len(words) > 72:
            cleaned = self._adjust_or_fallback(title, summary, chosen_hook, seed_facts)
            words = cleaned.split()

        word_count = len(words)
        duration = self.estimate_duration(word_count)

        logger.info(
            "Script generated for '%s': %d words, estimated %.1fs speech duration.",
            title,
            word_count,
            duration,
        )

        return GeneratedScript(
            hook=chosen_hook,
            body_text=cleaned,
            full_script=cleaned,
            word_count=word_count,
            estimated_duration_seconds=duration,
        )

    def _clean_script_text(self, text: str, chosen_hook: str) -> str:
        """Strip brackets, stage directions, narrator tags, and quotes."""
        # Remove parentheticals and bracketed notes
        cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", text)
        # Remove labels like 'Narrator:', 'Voiceover:', etc.
        cleaned = re.sub(r"^(narrator|voiceover|speaker|host):\s*", "", cleaned, flags=re.I | re.M)
        # Remove quotes and extra whitespace
        cleaned = " ".join(cleaned.replace('"', "").replace("'", "'").split())

        # If it doesn't start with the hook, prepend it
        if not cleaned.lower().startswith(chosen_hook.lower()[:15]):
            cleaned = f"{chosen_hook} {cleaned}"

        return cleaned

    def _adjust_or_fallback(
        self,
        title: str,
        summary: str,
        hook: str,
        facts: List[str],
    ) -> str:
        """Construct a clean 50-60 word script algorithmically if LLM wanders."""
        fact_1 = facts[0] if facts else summary
        fact_2 = facts[1] if len(facts) > 1 else "This biological process operates completely unnoticed."

        lines = [
            hook.strip(),
            f"Scientists recently confirmed that {title.lower()} is much stranger than anyone expected.",
            f"Specifically, {fact_1.lower()}.",
            f"{fact_2}.",
            "It turns out nature always has one last trick up its sleeve.",
        ]
        fallback = " ".join(lines)
        return fallback
