"""Shot Planner and Script Decomposition for Autonomous Faceless Shorts Factory.

Decomposes 45-65 word scripts into 5-7 punchy visual cuts, assigns visual emphasis,
and ensures shot cuts align with voiceover line transitions.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger("factory.shot_planner")


@dataclass
class ScriptCut:
    index: int
    text: str
    caps: str
    gap: float


class ShotPlanner:
    """Plans visual shot cuts and formats script.json for the video engine."""

    def plan_script_cuts(self, full_script: str, hook: str) -> List[ScriptCut]:
        """Split script into 5 to 7 visual lines/cuts."""
        # Clean script
        cleaned = " ".join(full_script.replace('"', "").replace("'", "'").split())

        # Split into raw sentences
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]

        cuts: List[ScriptCut] = []

        # Line 0 is always the hook
        cuts.append(
            ScriptCut(
                index=0,
                text=hook.strip(),
                caps=self._extract_caps(hook),
                gap=0.30,
            )
        )

        # Remaining sentences become subsequent cuts
        remaining_sentences = []
        for s in raw_sentences:
            if s.lower() != hook.lower().strip(".!?") and not s.lower().startswith(hook.lower()[:15]):
                remaining_sentences.append(s)

        # If a sentence is long (>14 words), split it at comma or conjunction
        sub_phrases: List[str] = []
        for sent in remaining_sentences:
            words = sent.split()
            if len(words) > 13 and "," in sent:
                parts = sent.split(",", 1)
                sub_phrases.append(parts[0].strip() + ",")
                sub_phrases.append(parts[1].strip())
            else:
                sub_phrases.append(sent)

        # Ensure we have between 4 and 7 total cuts
        for phrase in sub_phrases[:6]:
            if phrase:
                cuts.append(
                    ScriptCut(
                        index=len(cuts),
                        text=phrase,
                        caps=self._extract_caps(phrase),
                        gap=0.28 if phrase.endswith((".", "!", "?")) else 0.18,
                    )
                )

        # Ensure at least 4 cuts exist
        while len(cuts) < 4:
            cuts.append(
                ScriptCut(
                    index=len(cuts),
                    text="And that changed everything.",
                    caps="EVERYTHING",
                    gap=0.35,
                )
            )

        logger.info("Planned %d visual shot cuts from script.", len(cuts))
        return cuts

    def generate_script_json(
        self,
        cuts: List[ScriptCut],
        voice_id: str = "am_michael",
        speed: float = 1.05,
    ) -> Dict[str, Any]:
        """Create valid script.json data structure for the rendering engine."""
        return {
            "voice": voice_id,
            "speed": speed,
            "lead": 0.45,
            "outro": 0.90,
            "gap": 0.30,
            "lines": [
                {
                    "text": c.text,
                    "caps": c.caps,
                    "gap": c.gap,
                }
                for c in cuts
            ],
        }

    @staticmethod
    def _extract_caps(text: str) -> str:
        """Pick 1-3 prominent words to highlight in subtitles."""
        words = re.findall(r"\b[A-Za-z0-9]+\b", text)
        interesting = [w.upper() for w in words if len(w) > 4 or w.isdigit()]
        if interesting:
            return " ".join(interesting[:2])
        return words[0].upper() if words else "FACT"
