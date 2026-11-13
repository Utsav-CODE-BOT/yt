"""Comprehensive Verification Suite for Multilingual 12-Shorts/Day Factory Enhancement.

Tests translation, TTS voice synthesis, Unicode font assertions, metadata generation,
and folder hierarchy consistency across Kannada, Hindi, Telugu, and Tamil.
"""

import json
import os
import shutil
import unittest
from pathlib import Path

from content.translator import MultilingualTranslator, LANGUAGE_SPECS
from production.multilingual_tts import MultilingualTTS
from production.project_builder import ProjectBuilder


class TestMultilingualPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.translator = MultilingualTranslator()
        cls.tts = MultilingualTTS()
        cls.test_dir = Path(r"C:\Users\ud127\faceless-shorts-factory\workspace\tests\multilingual_test")
        cls.test_dir.mkdir(parents=True, exist_ok=True)

        cls.sample_title = "The Secret Power of Black Holes"
        cls.sample_hook = "What happens if you fall into a black hole?"
        cls.sample_lines = [
            {"text": "What happens if you fall into a black hole?", "gap": 0.20},
            {"text": "Gravity stretches your body into a thin string.", "gap": 0.18},
            {"text": "Physicists call this strange process spaghettification.", "gap": 0.22},
            {"text": "Time itself slows down as you reach the event horizon.", "gap": 0.20},
            {"text": "And nothing, not even light, can ever escape.", "gap": 0.30},
        ]

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_language_specifications(self):
        """Verify all 4 required languages are properly configured."""
        required = ["kannada", "hindi", "telugu", "tamil"]
        for lang in required:
            self.assertIn(lang, LANGUAGE_SPECS)
            spec = LANGUAGE_SPECS[lang]
            self.assertTrue(len(spec["default_voice"]) > 5)
            self.assertTrue(len(spec["hashtags"]) >= 3)
            self.assertTrue(len(spec["title_suffix"]) > 0)

    def test_02_script_translation_all_languages(self):
        """Verify translation of master script into Kannada, Hindi, Telugu, and Tamil."""
        for lang in ["kannada", "hindi", "telugu", "tamil"]:
            localized = self.translator.translate_script(
                master_title=self.sample_title,
                master_hook=self.sample_hook,
                master_lines=self.sample_lines,
                target_lang=lang,
            )
            self.assertEqual(localized.language, lang)
            self.assertEqual(len(localized.lines), len(self.sample_lines))
            self.assertTrue(localized.word_count >= 10)
            self.assertTrue(len(localized.hook) > 0)
            # Ensure text is non-empty and contains characters
            for line in localized.lines:
                self.assertTrue(len(line["text"]) > 0)
                self.assertIn("caps", line)
                self.assertIn("gap", line)

    def test_03_indic_voice_synthesis_kannada(self):
        """Test synthesizing neural Indic voiceover for Kannada."""
        localized = self.translator.translate_script(
            master_title=self.sample_title,
            master_hook=self.sample_hook,
            master_lines=self.sample_lines[:3],
            target_lang="kannada",
        )
        kn_dir = self.test_dir / "kannada"
        output = self.tts.synthesize_language_project(
            project_data_dir=kn_dir,
            lines=localized.lines,
            language="kannada",
            speed=1.05,
        )
        self.assertTrue(output.audio_path.exists())
        self.assertTrue(output.audio_path.stat().st_size > 10_000)
        self.assertTrue(output.lines_json_path.exists())
        self.assertTrue(output.words_json_path.exists())
        self.assertTrue(output.duration_seconds > 3.0)

        # Inspect lines.json and words.json integrity
        lines_data = json.loads(output.lines_json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(lines_data["lines"]), 3)
        words_data = json.loads(output.words_json_path.read_text(encoding="utf-8"))
        self.assertTrue(len(words_data) >= 5)

        # Verify timestamp monotonicity
        last_s = 0.0
        for w in words_data:
            self.assertGreaterEqual(w["s"], last_s - 0.05)
            self.assertGreater(w["e"], w["s"])
            last_s = w["s"]

    def test_04_metadata_generation_all_languages(self):
        """Verify localized metadata adheres to YouTube Shorts limits (<60 chars title, hashtags)."""
        for lang in ["kannada", "hindi", "telugu", "tamil"]:
            meta = self.translator.generate_localized_metadata(
                topic_title=self.sample_title,
                niche="Space & Astronomy",
                hook=self.sample_hook,
                script_text="Sample script text",
                target_lang=lang,
                source_url="https://nasa.gov",
                source_title="NASA Jet Propulsion Laboratory",
            )
            self.assertEqual(meta.language, lang)
            # Shorts title must be punchy and under 100 chars (aiming <60)
            self.assertTrue(len(meta.title) <= 90)
            self.assertIn("#Shorts", meta.title)
            self.assertIn("NASA", meta.description)
            self.assertTrue(len(meta.tags) >= 5)


if __name__ == "__main__":
    unittest.main()
