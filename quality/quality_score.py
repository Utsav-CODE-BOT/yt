"""Quality Score Aggregator for Autonomous Faceless Shorts Factory.

Combines technical, acoustic, caption, and visual evaluations into an overall QC score
and enforces the automated pass/fail gate before publishing.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from quality.audio_checks import AudioCheckResult, AudioChecks
from quality.caption_checks import CaptionCheckResult, CaptionChecks
from quality.technical_checks import TechnicalCheckResult, TechnicalChecks
from quality.visual_review import VisualCheckResult, VisualReview

logger = logging.getLogger("factory.qc.score")


@dataclass
class QualityGateResult:
    passed: bool
    overall_score: float
    technical_passed: bool
    audio_passed: bool
    caption_passed: bool
    visual_passed: bool
    all_issues: List[str]
    report: Dict[str, Any]


class QualityGate:
    """Orchestrates comprehensive post-render quality assurance."""

    def __init__(self, ffmpeg_exe: str = "ffmpeg"):
        self.technical_checks = TechnicalChecks(ffmpeg_exe=ffmpeg_exe)
        self.audio_checks = AudioChecks(ffmpeg_exe=ffmpeg_exe)
        self.caption_checks = CaptionChecks()
        self.visual_review = VisualReview()

    def evaluate_production(
        self,
        project_dir: Path,
        mp4_path: Path,
        sheet_path: Path,
    ) -> QualityGateResult:
        """Run all quality modules and compile final verdict."""
        logger.info("Evaluating quality gate for %s...", mp4_path.name)

        tech_res = self.technical_checks.evaluate_video(mp4_path)
        audio_res = self.audio_checks.evaluate_audio(mp4_path)
        cap_res = self.caption_checks.evaluate_captions(project_dir, tech_res.duration)
        vis_res = self.visual_review.evaluate_sheet(sheet_path)

        score = 100.0

        # Technical deductions
        if not tech_res.passed:
            score -= 35.0
        # Audio deductions
        if not audio_res.passed:
            score -= 25.0
        # Caption deductions
        if not cap_res.passed:
            score -= 20.0
        # Visual deductions
        if not vis_res.passed:
            score -= 10.0

        all_issues = tech_res.issues + audio_res.issues + cap_res.issues + vis_res.issues

        overall_score = max(0.0, min(100.0, score))
        # Hard fail if technical checks completely failed or score < 70
        passed = tech_res.passed and (overall_score >= 70.0)

        logger.info(
            "Quality gate verdict for %s: %s (Score: %.1f/100, Issues: %d)",
            mp4_path.name,
            "APPROVED" if passed else "REJECTED",
            overall_score,
            len(all_issues),
        )

        report = {
            "overall_score": overall_score,
            "passed": passed,
            "technical": asdict(tech_res),
            "audio": asdict(audio_res),
            "captions": asdict(cap_res),
            "visual": asdict(vis_res),
            "issues": all_issues,
        }

        return QualityGateResult(
            passed=passed,
            overall_score=overall_score,
            technical_passed=tech_res.passed,
            audio_passed=audio_res.passed,
            caption_passed=cap_res.passed,
            visual_passed=vis_res.passed,
            all_issues=all_issues,
            report=report,
        )
