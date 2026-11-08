"""Niche Manager and Rotation Engine for Autonomous Faceless Shorts Factory.

Coordinates the 10 core content niches, organizes them into audience pillars,
and rotates niches across the 3 daily production slots.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("factory.niche_manager")


@dataclass(frozen=True)
class NicheDefinition:
    id: str
    name: str
    pillar: str
    description: str
    preferred_styles: List[str]
    curiosity_keywords: List[str]
    enabled: bool = True
    priority: int = 1


NICHE_REGISTRY: Dict[str, NicheDefinition] = {
    "science_body": NicheDefinition(
        id="science_body",
        name="Science and human body",
        pillar="Human Biology & Anatomy",
        description="Fascinating human biology, physiological anomalies, and biological mechanisms.",
        preferred_styles=["inside-out", "deep-dive"],
        curiosity_keywords=["body", "brain", "cells", "organs", "heart", "dna", "biology"],
    ),
    "psychology": NicheDefinition(
        id="psychology",
        name="Psychology and human behaviour",
        pillar="Mind & Behavior",
        description="Cognitive biases, psychological phenomena, social experiments, and behavioral mysteries.",
        preferred_styles=["stick-story", "tall-tale"],
        curiosity_keywords=["psychology", "bias", "brain", "memory", "illusion", "behavior", "habit"],
    ),
    "interesting_facts": NicheDefinition(
        id="interesting_facts",
        name="Interesting facts",
        pillar="Curiosities & Wonders",
        description="Mind-bending, counter-intuitive facts about everyday things and the natural world.",
        preferred_styles=["deep-dive", "paper-atlas", "stick-story"],
        curiosity_keywords=["secret", "bizarre", "hidden", "discovery", "weird", "unbelievable"],
    ),
    "history_mysteries": NicheDefinition(
        id="history_mysteries",
        name="History and historical mysteries",
        pillar="True Stories & Historical Drama",
        description="Untold historical events, forgotten discoveries, and dramatic turning points.",
        preferred_styles=["paper-atlas", "night-file", "tall-tale"],
        curiosity_keywords=["ancient", "empire", "archaeology", "lost", "king", "war", "treasure"],
    ),
    "technology_ai": NicheDefinition(
        id="technology_ai",
        name="Technology and artificial intelligence",
        pillar="Future & Innovation",
        description="Cutting-edge computing, robotics, cybersecurity, and technological shifts.",
        preferred_styles=["deep-dive", "inside-out"],
        curiosity_keywords=["robot", "ai", "quantum", "chip", "algorithm", "supercomputer", "cyber"],
    ),
    "space_astronomy": NicheDefinition(
        id="space_astronomy",
        name="Space and astronomy",
        pillar="Cosmos & Deep Science",
        description="Extreme cosmic phenomena, black holes, rogue planets, and astrophysics.",
        preferred_styles=["night-file", "deep-dive"],
        curiosity_keywords=["black hole", "galaxy", "nasa", "planet", "telescope", "star", "nebula"],
    ),
    "nature_animals": NicheDefinition(
        id="nature_animals",
        name="Nature and animals",
        pillar="Natural Wonders",
        description="Extreme evolutionary adaptations, predator tactics, and deep-sea creatures.",
        preferred_styles=["deep-dive", "stick-story"],
        curiosity_keywords=["predator", "ocean", "evolution", "creature", "venom", "extinct"],
    ),
    "survival_practical": NicheDefinition(
        id="survival_practical",
        name="Survival and practical knowledge",
        pillar="Real-World Survival",
        description="Scientific survival physics, real disaster escapes, and critical practical laws.",
        preferred_styles=["stick-story", "night-file"],
        curiosity_keywords=["survival", "rescue", "escape", "avalanche", "hypothermia", "island"],
    ),
    "fitness_physiology": NicheDefinition(
        id="fitness_physiology",
        name="Fitness and human physiology",
        pillar="Human Biology & Anatomy",
        description="Muscle mechanics, endurance science, sleep architecture, and metabolism.",
        preferred_styles=["inside-out", "deep-dive"],
        curiosity_keywords=["muscle", "strength", "endurance", "sleep", "recovery", "metabolism"],
    ),
    "real_stories": NicheDefinition(
        id="real_stories",
        name="Extraordinary real-world stories",
        pillar="True Stories & Historical Drama",
        description="Unbelievable true events, audacious gambles, heists, and extraordinary human feats.",
        preferred_styles=["tall-tale", "paper-atlas", "night-file"],
        curiosity_keywords=["heist", "gamble", "millionaire", "soldier", "daring", "escape", "bank"],
    ),
}


class NicheManager:
    """Selects and balances niches across daily production slots."""

    def __init__(self, config_niches: Optional[Dict[str, Any]] = None):
        self.niches = dict(NICHE_REGISTRY)
        if config_niches:
            for key, val in config_niches.items():
                if key in self.niches and isinstance(val, dict):
                    enabled = val.get("enabled", self.niches[key].enabled)
                    priority = val.get("priority", self.niches[key].priority)
                    curr = self.niches[key]
                    self.niches[key] = NicheDefinition(
                        id=curr.id,
                        name=curr.name,
                        pillar=curr.pillar,
                        description=curr.description,
                        preferred_styles=curr.preferred_styles,
                        curiosity_keywords=curr.curiosity_keywords,
                        enabled=enabled,
                        priority=priority,
                    )

    def get_enabled_niches(self) -> List[NicheDefinition]:
        """Return list of all currently enabled niches."""
        return [n for n in self.niches.values() if n.enabled]

    def select_daily_niches(self, day_seed: int = 0) -> List[NicheDefinition]:
        """Select 3 distinct niches from different pillars for the day's 3 slots."""
        enabled = self.get_enabled_niches()
        if len(enabled) < 3:
            raise ValueError("At least 3 niches must be enabled in the configuration.")

        # Group by pillar to ensure content diversity
        pillars: Dict[str, List[NicheDefinition]] = {}
        for n in enabled:
            pillars.setdefault(n.pillar, []).append(n)

        selected: List[NicheDefinition] = []
        pillar_keys = list(pillars.keys())

        # Rotate through pillars based on day_seed
        for i in range(3):
            pillar_idx = (day_seed + i) % len(pillar_keys)
            pillar_name = pillar_keys[pillar_idx]
            niche_list = pillars[pillar_name]
            niche_idx = (day_seed // len(pillar_keys) + i) % len(niche_list)
            candidate = niche_list[niche_idx]

            # Avoid duplicates
            if candidate not in selected:
                selected.append(candidate)
            else:
                for alt in enabled:
                    if alt not in selected:
                        selected.append(alt)
                        break

        logger.info(
            "Selected daily niches (Seed %d): Slot 1: '%s', Slot 2: '%s', Slot 3: '%s'",
            day_seed,
            selected[0].name,
            selected[1].name,
            selected[2].name,
        )
        return selected[:3]
