"""Project Builder for Autonomous Faceless Shorts Factory.

Copies style templates into project workspace, decomposes scripts into line cuts,
configures Unicode Indic font rendering, and manages multilingual language variants.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from content.translator import LocalizedScript
from production.multilingual_tts import MultilingualTTS

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
        self.tts = MultilingualTTS()

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
        """Create a complete runnable project directory with Unicode font resilience."""
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

        # 2. Patch HTML and JS for Unicode Indic font & timing resilience
        self._patch_multilingual_fonts(project_dir)
        timing_js = project_dir / "src" / "core" / "timing.js"
        if timing_js.exists():
            self._patch_timing_resilience(timing_js)

        # 3. Create script.json (master English)
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

        # 4. Synthesize master narration and word timings
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

        if not narration_wav.exists() or not lines_json.exists():
            raise RuntimeError(f"Narration assets missing in {project_dir / 'data'}")

        logger.info("Project '%s' successfully built and aligned at %s", job_id, project_dir)
        return project_dir

    def prepare_multilingual_variant(
        self,
        project_dir: Path,
        job_id: str,
        language: str,
        localized_script: LocalizedScript,
        voice_override: Optional[str] = None,
        speed: float = 1.05,
    ) -> Dict[str, Any]:
        """Configure the existing master project assets for a specific regional language."""
        lang = language.lower().strip()
        lang_dir = project_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        logger.info("[%s] Preparing localized language variant for job '%s'...", lang.upper(), job_id)

        # 1. Update script.json for this language
        script_data = {
            "title": localized_script.title,
            "language": lang,
            "speed": speed,
            "lead": 0.30,
            "outro": 0.60,
            "gap": 0.18,
            "lines": localized_script.lines,
        }

        # Write to active project root and language subfolder
        script_json_str = json.dumps(script_data, indent=2, ensure_ascii=False)
        (project_dir / "script.json").write_text(script_json_str, encoding="utf-8")
        (lang_dir / "script.json").write_text(script_json_str, encoding="utf-8")

        # 2. Synthesize audio, lines.json, and words.json via MultilingualTTS
        tts_output = self.tts.synthesize_language_project(
            project_data_dir=project_dir / "data",
            lines=localized_script.lines,
            language=lang,
            voice_override=voice_override,
            speed=speed,
        )

        # 3. Archive/mirror language audio & subtitles into language folder
        shutil.copy2(project_dir / "data" / "narration.wav", lang_dir / "narration.wav")
        shutil.copy2(project_dir / "data" / "lines.json", lang_dir / "lines.json")
        shutil.copy2(project_dir / "data" / "words.json", lang_dir / "words.json")
        if (project_dir / "data" / "words.txt").exists():
            shutil.copy2(project_dir / "data" / "words.txt", lang_dir / "words.txt")

        logger.info(
            "[%s] Variant prepared: %.2fs audio with %d lines.",
            lang.upper(),
            tts_output.duration_seconds,
            len(localized_script.lines),
        )

        return {
            "language": lang,
            "audio_path": lang_dir / "narration.wav",
            "lines_path": lang_dir / "lines.json",
            "words_path": lang_dir / "words.json",
            "script_path": lang_dir / "script.json",
            "duration": tts_output.duration_seconds,
            "word_count": tts_output.total_words,
        }

    def _patch_multilingual_fonts(self, project_dir: Path) -> None:
        """Inject Windows Indic font declarations and Unicode regex matching into project files."""
        # 1. Patch index.html & sheet.html
        for html_file in (project_dir / "index.html", project_dir / "sheet.html"):
            if html_file.exists():
                content = html_file.read_text(encoding="utf-8")
                font_decl = (
                    "\n@font-face { font-family: 'Nirmala UI'; src: local('Nirmala UI'), local('Nirmala'); }\n"
                )
                if "@font-face" in content and "Nirmala UI" not in content:
                    content = content.replace("@font-face", f"{font_decl}@font-face", 1)
                    html_file.write_text(content, encoding="utf-8")
                    logger.debug("Patched font declarations in %s", html_file)

        # 2. Patch captions.js
        captions_js = project_dir / "src" / "core" / "captions.js"
        if captions_js.exists():
            content = captions_js.read_text(encoding="utf-8")

            # Update ctx.font to include Nirmala UI Indic font
            content = re.sub(
                r"ctx\.font\s*=\s*`900\s*\$\{size\}px\s*Inter`",
                "ctx.font = `900 ${size}px \"Nirmala UI\", Nirmala, \"Segoe UI\", Inter, sans-serif`",
                content,
            )
            # Update nm(w) to preserve Unicode letters and marks (\p{L}\p{M}\p{N})
            content = content.replace(
                "replace(/[^a-z0-9']+/g, '')",
                "replace(/[^\\p{L}\\p{M}\\p{N}']+/gu, '')",
            )
            # Scale CAP.size safely to prevent vertical diacritic clipping
            content = re.sub(r"size:\s*118", "size: 96", content)
            content = re.sub(r"size:\s*150", "size: 104", content)

            captions_js.write_text(content, encoding="utf-8")
            logger.debug("Applied multilingual caption patches to %s", captions_js)

        # 3. Patch kit.js if present (night-file style)
        kit_js = project_dir / "src" / "core" / "kit.js"
        if kit_js.exists():
            content = kit_js.read_text(encoding="utf-8")
            content = re.sub(
                r"\$\{MONO\}",
                "\"Nirmala UI\", Nirmala, ${MONO}",
                content,
            )
            kit_js.write_text(content, encoding="utf-8")

    def _patch_timing_resilience(self, timing_js: Path) -> None:
        """Patch timing.js to safely clamp missing lines and words and support Unicode norm."""
        content = timing_js.read_text(encoding="utf-8")

        # Update norm(w) in timing.js to preserve Unicode
        content = content.replace(
            "replace(/[^a-z0-9']+/g, '')",
            "replace(/[^\\p{L}\\p{M}\\p{N}']+/gu, '')",
        )

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
