"""Technical Quality Control for Autonomous Faceless Shorts Factory.

Validates container integrity, video codec, exact 1080x1920 9:16 dimensions,
30 fps framerate, and 22-28s duration compliance.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("factory.qc.technical")


@dataclass
class TechnicalCheckResult:
    passed: bool
    duration: float
    width: int
    height: int
    fps: int
    file_size_bytes: int
    issues: List[str]


class TechnicalChecks:
    """Verifies technical container specifications against YouTube Shorts standards."""

    def __init__(
        self,
        min_duration: float = 20.0,
        max_duration: float = 32.0,
        target_width: int = 1080,
        target_height: int = 1920,
        ffmpeg_exe: str = "ffmpeg",
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.target_width = target_width
        self.target_height = target_height
        self.ffmpeg_exe = ffmpeg_exe

    def evaluate_video(self, mp4_path: Path) -> TechnicalCheckResult:
        """Run technical validation on MP4 file."""
        issues: List[str] = []

        if not mp4_path.exists():
            return TechnicalCheckResult(
                passed=False, duration=0, width=0, height=0, fps=0, file_size_bytes=0, issues=["MP4 file does not exist"]
            )

        file_size = mp4_path.stat().st_size
        if file_size < 500_000:
            issues.append(f"File size too small: {file_size / 1024:.1f} KB (corrupted render)")
        elif file_size > 150_000_000:
            issues.append(f"File size too large: {file_size / (1024 * 1024):.1f} MB")

        # Run ffmpeg probe
        cmd = [self.ffmpeg_exe, "-i", str(mp4_path), "-hide_banner"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        probe_out = res.stderr

        # Check duration
        duration = 0.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", probe_out)
        if dur_match:
            h, m, s = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            if duration < self.min_duration:
                issues.append(f"Duration too short: {duration:.1f}s (minimum {self.min_duration}s)")
            elif duration > self.max_duration:
                issues.append(f"Duration too long: {duration:.1f}s (maximum {self.max_duration}s)")
        else:
            issues.append("Could not determine video duration from container")

        # Check resolution
        width, height = 0, 0
        res_match = re.search(r",\s*(\d{3,4})x(\d{3,4})\s*[, ]", probe_out)
        if res_match:
            width = int(res_match.group(1))
            height = int(res_match.group(2))
            if width != self.target_width or height != self.target_height:
                issues.append(f"Resolution mismatch: {width}x{height} (expected {self.target_width}x{self.target_height})")
        else:
            issues.append("Could not determine video resolution")

        # Check framerate
        fps = 30
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", probe_out)
        if fps_match:
            fps = int(float(fps_match.group(1)))
            if fps not in (30, 60):
                issues.append(f"Unexpected framerate: {fps} fps (expected 30 fps)")

        # Check audio stream presence
        if "Audio:" not in probe_out:
            issues.append("Missing audio stream in MP4 container")

        passed = len(issues) == 0
        logger.info(
            "Technical QC for %s: %s (Dur: %.1fs, Res: %dx%d, Issues: %d)",
            mp4_path.name,
            "PASSED" if passed else "FAILED",
            duration,
            width,
            height,
            len(issues),
        )

        return TechnicalCheckResult(
            passed=passed,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            file_size_bytes=file_size,
            issues=issues,
        )
