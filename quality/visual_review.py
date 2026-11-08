"""Visual Review QC for Autonomous Faceless Shorts Factory.

Validates contact sheet rendering and ensures frames contain active visual content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("factory.qc.visual")


@dataclass
class VisualCheckResult:
    passed: bool
    sheet_exists: bool
    sheet_size_bytes: int
    issues: List[str]


class VisualReview:
    """Verifies that visual contact sheets were generated with valid canvas content."""

    def evaluate_sheet(self, sheet_path: Optional[Path]) -> VisualCheckResult:
        issues: List[str] = []

        if not sheet_path or not sheet_path.exists():
            issues.append("Visual contact sheet (review/all.jpg) not generated")
            return VisualCheckResult(passed=False, sheet_exists=False, sheet_size_bytes=0, issues=issues)

        file_size = sheet_path.stat().st_size
        if file_size < 15_000:
            issues.append(f"Visual contact sheet suspiciously small: {file_size} bytes (possible blank canvas)")

        passed = len(issues) == 0
        return VisualCheckResult(
            passed=passed,
            sheet_exists=True,
            sheet_size_bytes=file_size,
            issues=issues,
        )
