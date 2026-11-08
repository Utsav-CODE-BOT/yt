"""Video Renderer for Autonomous Faceless Shorts Factory.

Coordinates headless Chrome canvas screencast capture, procedural audio mixing,
contact sheet generation, and technical MP4 validation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("factory.renderer")


@dataclass
class RenderResult:
    job_id: str
    mp4_path: Path
    sheet_path: Optional[Path]
    duration_seconds: float
    width: int
    height: int
    fps: int
    file_size_bytes: int
    render_time_seconds: float


class VideoRenderer:
    """Invokes headless Chrome capture and procedural audio mixing."""

    def __init__(
        self,
        node_exe: str = "node",
        python_exe: str | Path = r"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe",
        exports_pending_dir: str | Path = r"C:\Users\ud127\faceless-shorts-factory\workspace\exports\pending",
        ffmpeg_exe: str = "ffmpeg",
    ):
        self.node_exe = node_exe
        self.python_exe = Path(python_exe)
        self.ffmpeg_exe = ffmpeg_exe
        self.exports_pending_dir = Path(exports_pending_dir)
        self.exports_pending_dir.mkdir(parents=True, exist_ok=True)

    def render(self, project_dir: Path, job_id: str) -> RenderResult:
        """Execute the full rendering sequence for a project."""
        t_start = time.time()
        logger.info("Starting video render pipeline for job '%s'...", job_id)

        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Ensure Chrome path is set
        env["CHROME"] = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

        # 1. Generate cues: node tools/capture.mjs cues
        capture_mjs = project_dir / "tools" / "capture.mjs"
        mix_py = project_dir / "tools" / "mix.py"

        logger.info("[%s] Generating sound cues...", job_id)
        cmd_cues = [self.node_exe, str(capture_mjs), "cues"]
        res_cues = subprocess.run(cmd_cues, cwd=project_dir, capture_output=True, text=True, env=env)
        if res_cues.returncode != 0:
            logger.warning("[%s] cues command stderr: %s", job_id, res_cues.stderr)

        # 2. Procedural audio mix: python tools/mix.py
        logger.info("[%s] Synthesizing procedural audio mix...", job_id)
        cmd_mix = [str(self.python_exe), str(mix_py)]
        res_mix = subprocess.run(cmd_mix, cwd=project_dir, capture_output=True, text=True, env=env)
        if res_mix.returncode != 0:
            logger.warning("[%s] mix.py stderr: %s", job_id, res_mix.stderr)

        # 3. Render video in Headless Chrome: node tools/capture.mjs video renders/{job_id}.mp4
        output_rel_mp4 = Path("renders") / f"{job_id}.mp4"
        rendered_mp4 = project_dir / output_rel_mp4

        if rendered_mp4.exists() and rendered_mp4.stat().st_size > 1_000_000:
            logger.info("[%s] Existing rendered MP4 found (%.1f MB). Skipping re-capture.", job_id, rendered_mp4.stat().st_size / (1024 * 1024))
        else:
            logger.info("[%s] Capturing frames via Headless Chrome to %s...", job_id, output_rel_mp4)
            cmd_render = [self.node_exe, str(capture_mjs), "video", str(output_rel_mp4)]
            res_render = subprocess.run(cmd_render, cwd=project_dir, capture_output=True, text=True, env=env)
            if res_render.returncode != 0:
                logger.error("[%s] Chrome capture failed: %s\n%s", job_id, res_render.stdout, res_render.stderr)
                raise RuntimeError(f"Headless Chrome capture failed: {res_render.stderr}")

        # 4. Generate contact sheet: node tools/capture.mjs sheet review/all.jpg
        review_sheet = project_dir / "review" / "all.jpg"
        if not review_sheet.exists() or review_sheet.stat().st_size < 10_000:
            logger.info("[%s] Generating visual review sheet...", job_id)
            cmd_sheet = [self.node_exe, str(capture_mjs), "sheet", "review/all.jpg"]
            subprocess.run(cmd_sheet, cwd=project_dir, capture_output=True, text=True, env=env)

        rendered_mp4 = project_dir / output_rel_mp4
        if not rendered_mp4.exists() or rendered_mp4.stat().st_size < 100_000:
            raise FileNotFoundError(f"Rendered video file not found or corrupted: {rendered_mp4}")

        # 5. Extract video metadata via ffprobe or ffmpeg
        meta = self._probe_video(rendered_mp4)

        # 6. Copy to workspace/exports/pending/{job_id}.mp4
        export_dest = self.exports_pending_dir / f"{job_id}.mp4"
        shutil.copy2(rendered_mp4, export_dest)

        t_elapsed = time.time() - t_start
        logger.info(
            "Render complete for job '%s': %.1fs video rendered in %.1fs (Size: %.1f MB). Exported to %s",
            job_id,
            meta.get("duration", 0.0),
            t_elapsed,
            export_dest.stat().st_size / (1024 * 1024),
            export_dest,
        )

        return RenderResult(
            job_id=job_id,
            mp4_path=export_dest,
            sheet_path=review_sheet if review_sheet.exists() else None,
            duration_seconds=meta.get("duration", 25.0),
            width=meta.get("width", 1080),
            height=meta.get("height", 1920),
            fps=meta.get("fps", 30),
            file_size_bytes=export_dest.stat().st_size,
            render_time_seconds=t_elapsed,
        )

    def _probe_video(self, mp4_path: Path) -> Dict[str, Any]:
        """Probe MP4 container for exact duration, dimensions, and framerate."""
        cmd = [
            self.ffmpeg_exe,
            "-i",
            str(mp4_path),
            "-hide_banner",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = res.stderr

        meta = {"duration": 25.0, "width": 1080, "height": 1920, "fps": 30}

        # Parse duration: Duration: 00:00:24.83
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out)
        if dur_match:
            h, m, s = dur_match.groups()
            meta["duration"] = int(h) * 3600 + int(m) * 60 + float(s)

        # Parse resolution: 1080x1920
        res_match = re.search(r",\s*(\d{3,4})x(\d{3,4})\s*[, ]", out)
        if res_match:
            meta["width"] = int(res_match.group(1))
            meta["height"] = int(res_match.group(2))

        # Parse fps: 30 fps
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", out)
        if fps_match:
            meta["fps"] = int(float(fps_match.group(1)))

        return meta
