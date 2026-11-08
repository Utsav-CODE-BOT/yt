"""Script Validation Engine for Autonomous Faceless Shorts Factory.

Performs deterministic quality gates on generated scripts:
word count, duration estimation, opening hook discipline, readability, and forbidden CTA checks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger("factory.script_validator")

FORBIDDEN_PHRASES = [
    r"\bsubscribe\b",
    r"\blike and share\b",
    r"\bsmash the like\b",
    r"\bcomment down below\b",
    r"\bfollow for more\b",
    r"\bhey guys\b",
    r"\bwelcome back\b",
    r"\byou won'?t believe\b",
]


@dataclass
class ScriptValidationResult:
    passed: bool
    word_count: int
    estimated_duration: float
    flesch_reading_ease: float
    reading_grade_level: float
    issues: List[str]
    metrics: Dict[str, float]


class ScriptValidator:
    """Enforces rigorous editorial and technical constraints on short scripts."""

    def __init__(self, min_words: int = 40, max_words: int = 70, min_duration: float = 20.0, max_duration: float = 28.5):
        self.min_words = min_words
        self.max_words = max_words
        self.min_duration = min_duration
        self.max_duration = max_duration

    @staticmethod
    def count_syllables(word: str) -> int:
        """Rough syllable counter for Flesch-Kincaid metric calculation."""
        w = word.lower().strip(".,!?:;\"'")
        if not w:
            return 1
        if len(w) <= 3:
            return 1
        w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
        w = re.sub(r"^y", "", w)
        matches = re.findall(r"[aeiouy]{1,2}", w)
        return max(1, len(matches))

    def validate(self, script_text: str, wpm: float = 140.0) -> ScriptValidationResult:
        """Run all editorial gates and return verdict."""
        issues: List[str] = []
        words = script_text.split()
        word_count = len(words)
        duration = (word_count / wpm) * 60.0

        # 1. Word count constraint
        if word_count < self.min_words:
            issues.append(f"Too short: {word_count} words (minimum {self.min_words})")
        elif word_count > self.max_words:
            issues.append(f"Too long: {word_count} words (maximum {self.max_words})")

        # 2. Duration constraint
        if duration < self.min_duration:
            issues.append(f"Duration too short: {duration:.1f}s (minimum {self.min_duration:.1f}s)")
        elif duration > self.max_duration:
            issues.append(f"Duration too long: {duration:.1f}s (maximum {self.max_duration:.1f}s)")

        # 3. Hook sentence constraint
        sentences = [s.strip() for s in re.split(r"[.!?]+", script_text) if s.strip()]
        if not sentences:
            issues.append("No sentences detected.")
        else:
            first_sentence_words = len(sentences[0].split())
            if first_sentence_words > 14:
                issues.append(f"Opening hook sentence too long: {first_sentence_words} words (maximum 14)")

        # 4. Forbidden CTA / Cheap Engagement Check
        for pat in FORBIDDEN_PHRASES:
            if re.search(pat, script_text, re.I):
                issues.append(f"Contains prohibited engagement phrase matching pattern '{pat}'")

        # 5. Readability Analysis (Flesch Reading Ease and Kincaid Grade)
        total_syllables = sum(self.count_syllables(w) for w in words)
        num_sentences = max(1, len(sentences))
        words_per_sentence = word_count / num_sentences
        syllables_per_word = total_syllables / max(1, word_count)

        # Flesch Reading Ease formula
        flesch_ease = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        # Flesch-Kincaid Grade Level formula
        grade_level = (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59

        if grade_level > 10.0:
            issues.append(f"Language too complex: Grade Level {grade_level:.1f} (target <= 9.0)")

        passed = len(issues) == 0

        logger.info(
            "Script validation: %s (Words: %d, Dur: %.1fs, Ease: %.1f, Grade: %.1f, Issues: %d)",
            "PASSED" if passed else "FAILED",
            word_count,
            duration,
            flesch_ease,
            grade_level,
            len(issues),
        )

        return ScriptValidationResult(
            passed=passed,
            word_count=word_count,
            estimated_duration=duration,
            flesch_reading_ease=flesch_ease,
            reading_grade_level=grade_level,
            issues=issues,
            metrics={
                "words_per_sentence": words_per_sentence,
                "syllables_per_word": syllables_per_word,
                "duration_seconds": duration,
            },
        )
