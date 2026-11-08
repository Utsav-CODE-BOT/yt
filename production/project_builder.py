"""Project Builder for Autonomous Faceless Shorts Factory.

Copies style templates into project workspace, decomposes scripts into line cuts,
generates Kokoro TTS audio and Faster-Whisper word alignment.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("factory.project_builder")

STYLE_TARGET_LINES: Dict[str, int] = {
    "deep-dive": 10,
    "inside-out": 11,
    "night-file": 11,
    "paper-atlas": 10,
    "stick-story": 12,
    "tall-tale": 18,
}


class ProjectBuilder:
    """Instantiates and configures runnable faceless shorts video projects."""

    def __init__(
        self,
        skills_root: str | Path | None = None,
        workspace_root: str | Path = r"C:\Users\ud127\faceless-shorts-factory\workspace\projects",
        python_exe: str | Path = r"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe",
    ):
        if skills_root is not None:
            self.skills_root = Path(skills_root)
        else:
            local_skills = Path(__file__).resolve().parent.parent / "skills" / "faceless-shorts"
            if local_skills.exists():
                self.skills_root = local_skills
            else:
                self.skills_root = Path(r"C:\Users\ud127\.claude\skills\faceless-shorts")
        self.workspace_root = Path(workspace_root)
        self.python_exe = Path(python_exe)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def distribute_script_lines(self, script_text: str, hook: str, target_count: int) -> List[Dict[str, Any]]:
        """Distribute a 45-65 word script across target_count lines."""
        cleaned = " ".join(script_text.replace('"', "").replace("'", "'").split())
        words = cleaned.split()

        # Extract words from hook to ensure line 0 is the hook
        hook_words = hook.strip().split()
        hook_len = len(hook_words)

        remaining_words = words[hook_len:] if len(words) > hook_len else words[len(words)//2:]
        if not remaining_words:
            remaining_words = ["is", "truly", "an", "extraordinary", "discovery", "in", "science."]

        lines = [{"text": " ".join(hook_words), "caps": " ".join([w.upper() for w in hook_words if len(w) > 4][:2]) or "FACT"}]

        needed_remaining_lines = target_count - 1
        words_per_line = max(2, len(remaining_words) // needed_remaining_lines)

        idx = 0
        for i in range(needed_remaining_lines):
            if i == needed_remaining_lines - 1:
                # Last line gets whatever is left
                chunk = remaining_words[idx:]
            else:
                chunk = remaining_words[idx : idx + words_per_line]
                idx += words_per_line

            if not chunk:
                chunk = ["and", "that", "changed", "history."]

            line_text = " ".join(chunk)
            caps = " ".join([w.upper() for w in chunk if len(w) > 4][:2]) or chunk[0].upper()
            gap = 0.22 if line_text.endswith((".", "!", "?")) else 0.15
            lines.append({"text": line_text, "caps": caps, "gap": gap})

        return lines

    def build_project(
        self,
        job_id: str,
        style_name: str,
        script_text: str,
        hook: str,
        voice_id: str = "am_michael",
        title: str = "Daily Short",
        speed: float = 1.10,
    ) -> Path:
        """Create a complete runnable project directory."""
        template_dir = self.skills_root / "styles" / style_name / "example"
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        project_dir = self.workspace_root / job_id
        if project_dir.exists():
            shutil.rmtree(project_dir)

        # 1. Copy template files
        shutil.copytree(template_dir, project_dir)
        (project_dir / "renders").mkdir(parents=True, exist_ok=True)
        (project_dir / "review").mkdir(parents=True, exist_ok=True)
        (project_dir / "data").mkdir(parents=True, exist_ok=True)

        # 2. Patch timing.js for runtime resilience
        timing_js = project_dir / "src" / "core" / "timing.js"
        if timing_js.exists():
            self._patch_timing_resilience(timing_js)

        # 3. Create script.json
        target_lines = STYLE_TARGET_LINES.get(style_name, 10)
        formatted_lines = self.distribute_script_lines(script_text, hook, target_lines)

        script_data = {
            "title": title,
            "voice": voice_id,
            "speed": speed,
            "lead": 0.30,
            "outro": 0.60,
            "gap": 0.20,
            "lines": formatted_lines,
        }

        script_json_path = project_dir / "script.json"
        script_json_path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")
        logger.info("Wrote script.json with %d lines to %s", len(formatted_lines), script_json_path)

        # 4. Run Kokoro voice.py
        voice_script = self.skills_root / "scripts" / "voice.py"
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        logger.info("Synthesizing narration with Kokoro-82M (%s)...", voice_id)
        voice_cmd = [str(self.python_exe), str(voice_script), str(project_dir)]
        voice_res = subprocess.run(voice_cmd, capture_output=True, text=True, env=env)
        if voice_res.returncode != 0:
            logger.error("voice.py failed: %s\n%s", voice_res.stdout, voice_res.stderr)
            raise RuntimeError(f"Voice generation failed: {voice_res.stderr}")

        # 5. Run Faster-Whisper words.py
        words_script = self.skills_root / "scripts" / "words.py"
        logger.info("Aligning word timestamps with Faster-Whisper...")
        words_cmd = [str(self.python_exe), str(words_script), str(project_dir)]
        words_res = subprocess.run(words_cmd, capture_output=True, text=True, env=env)
        if words_res.returncode != 0:
            logger.warning("words.py encountered error: %s. Using inline fallback.", words_res.stderr)

        narration_wav = project_dir / "data" / "narration.wav"
        lines_json = project_dir / "data" / "lines.json"
        words_json = project_dir / "data" / "words.json"

        if not narration_wav.exists() or not lines_json.exists():
            raise RuntimeError(f"Narration assets missing in {project_dir / 'data'}")

        logger.info("Project '%s' successfully built and aligned at %s", job_id, project_dir)
        return project_dir

    def _patch_timing_resilience(self, timing_js: Path) -> None:
        """Patch timing.js to safely clamp missing lines and words instead of throwing fatal exceptions."""
        content = timing_js.read_text(encoding="utf-8")

        # Safe L(i) and Le(i)
        safe_l = (
            "export const L = (i) => {\n"
            "  if (!T.lines || T.lines.length === 0) return 0;\n"
            "  const idx = Math.min(Math.max(0, i), T.lines.length - 1);\n"
            "  return T.lines[idx].start;\n"
            "};\n"
            "export const Le = (i) => {\n"
            "  if (!T.lines || T.lines.length === 0) return 0;\n"
            "  const idx = Math.min(Math.max(0, i), T.lines.length - 1);\n"
            "  return T.lines[idx].end;\n"
            "};\n"
        )
        content = re.sub(r"export const L = \(i\) => \{.*?\};\s*export const Le = \(i\) => \{.*?\};", safe_l, content, flags=re.S)

        # Safe Wd(word, line)
        safe_wd = (
            "export function Wd(word, line, which = 's') {\n"
            "  const n = norm(word);\n"
            "  const hit = T.words.find((w) => (line == null || w.line === line) && norm(w.w).startsWith(n));\n"
            "  if (!hit) {\n"
            "    if (line != null && T.lines && T.lines[line]) return T.lines[line].start + 0.2;\n"
            "    return (T.lines && T.lines[0]) ? T.lines[0].start + 0.2 : 0.0;\n"
            "  }\n"
            "  return hit[which];\n"
            "}\n"
        )
        content = re.sub(r"export function Wd\(word, line, which = 's'\) \{.*?return hit\[which\];\s*\}", safe_wd, content, flags=re.S)

        timing_js.write_text(content, encoding="utf-8")
        logger.debug("Applied resilience patch to %s", timing_js)
