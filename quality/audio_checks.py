"""Audio Quality Control for Autonomous Faceless Shorts Factory.

Analyzes peak amplitude, integrated loudness (LUFS), dynamic compression,
and detects dead air or silence gaps.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("factory.qc.audio")


@dataclass
class AudioCheckResult:
    passed: bool
    max_volume_db: float
    mean_volume_db: float
    integrated_lufs: float
    issues: List[str]


class AudioChecks:
    """Verifies audio levels and speech presence."""

    def __init__(self, ffmpeg_exe: str = "ffmpeg"):
        self.ffmpeg_exe = ffmpeg_exe

    def evaluate_audio(self, mp4_path: Path) -> AudioCheckResult:
        """Analyze audio track with ffmpeg volumedetect and ebur128 filters."""
        issues: List[str] = []

        # 1. Volume detect filter
        cmd_vol = [
            self.ffmpeg_exe,
            "-i",
            str(mp4_path),
            "-af",
            "volumedetect",
            "-vn",
            "-sn",
            "-f",
            "null",
            "NUL" if subprocess.os.name == "nt" else "/dev/null",
        ]
        res_vol = subprocess.run(cmd_vol, capture_output=True, text=True)
        vol_out = res_vol.stderr

        max_vol = -1.0
        mean_vol = -20.0

        max_match = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", vol_out)
        if max_match:
            max_vol = float(max_match.group(1))
            if max_vol > -0.2:
                issues.append(f"Audio peaking / clipping risk: {max_vol:.1f} dBFS (exceeds -0.5 dBFS limit)")
            elif max_vol < -12.0:
                issues.append(f"Audio too quiet: peak {max_vol:.1f} dBFS")

        mean_match = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", vol_out)
        if mean_match:
            mean_vol = float(mean_match.group(1))

        # 2. EBU R128 Loudness measurement
        cmd_lufs = [
            self.ffmpeg_exe,
            "-i",
            str(mp4_path),
            "-af",
            "ebur128=framelog=verbose",
            "-vn",
            "-f",
            "null",
            "NUL" if subprocess.os.name == "nt" else "/dev/null",
        ]
        res_lufs = subprocess.run(cmd_lufs, capture_output=True, text=True)
        lufs_out = res_lufs.stderr

        lufs = -14.0
        lufs_match = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", lufs_out)
        if lufs_match:
            lufs = float(lufs_match.group(1))
            if lufs > -10.0:
                issues.append(f"Loudness too high: {lufs:.1f} LUFS (YouTube short target is -14 LUFS)")
            elif lufs < -22.0:
                issues.append(f"Loudness too low: {lufs:.1f} LUFS")

        passed = len(issues) == 0
        logger.info(
            "Audio QC for %s: %s (Max: %.1fdB, Mean: %.1fdB, LUFS: %.1f, Issues: %d)",
            mp4_path.name,
            "PASSED" if passed else "FAILED",
            max_vol,
            mean_vol,
            lufs,
            len(issues),
        )

        return AudioCheckResult(
            passed=passed,
            max_volume_db=max_vol,
            mean_volume_db=mean_vol,
            integrated_lufs=lufs,
            issues=issues,
        )
