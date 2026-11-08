"""Style and Voice Selector for Autonomous Faceless Shorts Factory.

Maps niches to the 6 core visual styles, balances style variety across daily slots,
and assigns appropriate Kokoro TTS voices.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger("factory.style_selector")

AVAILABLE_STYLES = [
    "deep-dive",
    "inside-out",
    "night-file",
    "paper-atlas",
    "stick-story",
    "tall-tale",
]

STYLE_NICHE_AFFINITIES: Dict[str, List[str]] = {
    "Science and human body": ["inside-out", "deep-dive"],
    "Psychology and human behaviour": ["stick-story", "tall-tale"],
    "Interesting facts": ["deep-dive", "paper-atlas", "stick-story"],
    "History and historical mysteries": ["paper-atlas", "night-file", "tall-tale"],
    "Technology and artificial intelligence": ["deep-dive", "inside-out"],
    "Space and astronomy": ["night-file", "deep-dive"],
    "Nature and animals": ["deep-dive", "stick-story"],
    "Survival and practical knowledge": ["stick-story", "night-file"],
    "Fitness and human physiology": ["inside-out", "deep-dive"],
    "Extraordinary real-world stories": ["tall-tale", "paper-atlas", "night-file"],
}

VOICE_MAP: Dict[str, str] = {
    "deep-dive": "am_michael",
    "inside-out": "af_heart",
    "night-file": "bm_george",
    "paper-atlas": "bm_fable",
    "stick-story": "am_puck",
    "tall-tale": "am_michael",
}


@dataclass
class StyleSelection:
    style_name: str
    voice_id: str
    speed: float = 1.05
    lead: float = 0.45
    outro: float = 0.90
    gap: float = 0.32


class StyleSelector:
    """Selects visual style and voice while ensuring distinct styles per daily batch."""

    def select_style_for_slot(
        self,
        niche: str,
        slot_number: int,
        used_styles_today: Optional[Set[str]] = None,
    ) -> StyleSelection:
        """Select a suitable style that has not yet been used today."""
        used = used_styles_today or set()
        candidates = STYLE_NICHE_AFFINITIES.get(niche, AVAILABLE_STYLES)

        chosen_style: Optional[str] = None
        for s in candidates:
            if s not in used and s in AVAILABLE_STYLES:
                chosen_style = s
                break

        # Fallback if all candidates are used
        if not chosen_style:
            for s in AVAILABLE_STYLES:
                if s not in used:
                    chosen_style = s
                    break

        if not chosen_style:
            chosen_style = candidates[0] if candidates else "tall-tale"

        voice_id = VOICE_MAP.get(chosen_style, "am_michael")

        logger.info(
            "Selected style '%s' with voice '%s' for slot %d (Niche: %s)",
            chosen_style,
            voice_id,
            slot_number,
            niche,
        )

        return StyleSelection(
            style_name=chosen_style,
            voice_id=voice_id,
            speed=1.05,
            lead=0.45,
            outro=0.90,
            gap=0.32,
        )
