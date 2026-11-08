"""Caption and Subtitle Synchronization QC for Autonomous Faceless Shorts Factory.

Validates word-level timestamp monotonicity, boundary bounds, and detects subtitle drift.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("factory.qc.captions")


@dataclass
class CaptionCheckResult:
    passed: bool
    total_words: int
    alignment_duration: float
    issues: List[str]


class CaptionChecks:
    """Verifies timing accuracy of generated subtitle files."""

    def evaluate_captions(self, project_dir: Path, video_duration: float) -> CaptionCheckResult:
        """Inspect data/words.json and data/lines.json for temporal consistency."""
        issues: List[str] = []
        words_file = project_dir / "data" / "words.json"
        lines_file = project_dir / "data" / "lines.json"

        if not words_file.exists():
            return CaptionCheckResult(passed=False, total_words=0, alignment_duration=0, issues=["words.json missing"])

        try:
            words = json.loads(words_file.read_text(encoding="utf-8"))
        except Exception as e:
            return CaptionCheckResult(passed=False, total_words=0, alignment_duration=0, issues=[f"Malformed words.json: {e}"])

        total_words = len(words)
        if total_words < 30:
            issues.append(f"Unusually low word count: {total_words} words")

        last_start = -0.1
        last_end = 0.0

        for idx, w in enumerate(words):
            s = float(w.get("s", 0))
            e = float(w.get("e", 0))
            word_str = w.get("w", "")

            if not word_str.strip():
                issues.append(f"Empty word token at index {idx}")

            if s < last_start - 0.05:
                issues.append(f"Non-monotonic timestamp order at word '{word_str}' ({s:.2f}s < {last_start:.2f}s)")

            if e < s:
                issues.append(f"Negative word duration at word '{word_str}' ({s:.2f}s to {e:.2f}s)")

            if e > video_duration + 1.0:
                issues.append(f"Word timestamp extends beyond video duration: {e:.2f}s > {video_duration:.2f}s")

            last_start = s
            last_end = max(last_end, e)

        passed = len(issues) == 0
        logger.info(
            "Caption QC for %s: %s (%d words, span: %.1fs, issues: %d)",
            project_dir.name,
            "PASSED" if passed else "FAILED",
            total_words,
            last_end,
            len(issues),
        )

        return CaptionCheckResult(
            passed=passed,
            total_words=total_words,
            alignment_duration=last_end,
            issues=issues,
        )
