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
    "history_ancient": NicheDefinition(
        id="history_ancient",
        name="Ancient history and civilizations",
        pillar="Ancient Civilizations & Archaeology",
        description="Ancient engineering marvels, Rome, Egypt, forgotten empires, and ancient archaeological discoveries.",
        preferred_styles=["paper-atlas", "deep-dive"],
        curiosity_keywords=["ancient", "rome", "egypt", "pyramid", "greece", "archaeology", "bronze age", "empire", "emperor"],
        enabled=True,
    ),
    "history_mysteries": NicheDefinition(
        id="history_mysteries",
        name="History and historical mysteries",
        pillar="Lost Civilizations & Enigmas",
        description="Untold historical enigmas, lost legions, deciphered manuscripts, and mysterious historical anomalies.",
        preferred_styles=["paper-atlas", "night-file"],
        curiosity_keywords=["ancient", "empire", "archaeology", "lost", "king", "war", "treasure", "mystery", "voynich"],
        enabled=True,
    ),
    "history_turning_points": NicheDefinition(
        id="history_turning_points",
        name="Historical turning points and extraordinary events",
        pillar="Turning Points & True Drama",
        description="Unbelievable historical deceptions, bizarre battles, wartime hoaxes, and moments that altered history.",
        preferred_styles=["tall-tale", "paper-atlas", "night-file"],
        curiosity_keywords=["battle", "napoleon", "war", "deception", "heist", "treaty", "revolution", "bizarre", "soldier"],
        enabled=True,
    ),
    "science_body": NicheDefinition(
        id="science_body",
        name="Science and human body",
        pillar="Human Biology & Anatomy",
        description="Fascinating human biology, physiological anomalies, and biological mechanisms.",
        preferred_styles=["inside-out", "deep-dive"],
        curiosity_keywords=["body", "brain", "cells", "organs", "heart", "dna", "biology"],
        enabled=False,
    ),
    "psychology": NicheDefinition(
        id="psychology",
        name="Psychology and human behaviour",
        pillar="Mind & Behavior",
        description="Cognitive biases, psychological phenomena, social experiments, and behavioral mysteries.",
        preferred_styles=["stick-story", "tall-tale"],
        curiosity_keywords=["psychology", "bias", "brain", "memory", "illusion", "behavior", "habit"],
        enabled=False,
    ),
    "interesting_facts": NicheDefinition(
        id="interesting_facts",
        name="Interesting facts",
        pillar="Curiosities & Wonders",
        description="Mind-bending, counter-intuitive facts about everyday things and the natural world.",
        preferred_styles=["deep-dive", "paper-atlas", "stick-story"],
        curiosity_keywords=["secret", "bizarre", "hidden", "discovery", "weird", "unbelievable"],
        enabled=False,
    ),
    "technology_ai": NicheDefinition(
        id="technology_ai",
        name="Technology and artificial intelligence",
        pillar="Future & Innovation",
        description="Cutting-edge computing, robotics, cybersecurity, and technological shifts.",
        preferred_styles=["deep-dive", "inside-out"],
        curiosity_keywords=["robot", "ai", "quantum", "chip", "algorithm", "supercomputer", "cyber"],
        enabled=False,
    ),
    "space_astronomy": NicheDefinition(
        id="space_astronomy",
        name="Space and astronomy",
        pillar="Cosmos & Deep Science",
        description="Extreme cosmic phenomena, black holes, rogue planets, and astrophysics.",
        preferred_styles=["night-file", "deep-dive"],
        curiosity_keywords=["black hole", "galaxy", "nasa", "planet", "telescope", "star", "nebula"],
        enabled=False,
    ),
    "nature_animals": NicheDefinition(
        id="nature_animals",
        name="Nature and animals",
        pillar="Natural Wonders",
        description="Extreme evolutionary adaptations, predator tactics, and deep-sea creatures.",
        preferred_styles=["deep-dive", "stick-story"],
        curiosity_keywords=["predator", "ocean", "evolution", "creature", "venom", "extinct"],
        enabled=False,
    ),
    "survival_practical": NicheDefinition(
        id="survival_practical",
        name="Survival and practical knowledge",
        pillar="Real-World Survival",
        description="Scientific survival physics, real disaster escapes, and critical practical laws.",
        preferred_styles=["stick-story", "night-file"],
        curiosity_keywords=["survival", "rescue", "escape", "avalanche", "hypothermia", "island"],
        enabled=False,
    ),
    "fitness_physiology": NicheDefinition(
        id="fitness_physiology",
        name="Fitness and human physiology",
        pillar="Human Biology & Anatomy",
        description="Muscle mechanics, endurance science, sleep architecture, and metabolism.",
        preferred_styles=["inside-out", "deep-dive"],
        curiosity_keywords=["muscle", "strength", "endurance", "sleep", "recovery", "metabolism"],
        enabled=False,
    ),
    "real_stories": NicheDefinition(
        id="real_stories",
        name="Extraordinary real-world stories",
        pillar="True Stories & Historical Drama",
        description="Unbelievable true events, audacious gambles, heists, and extraordinary human feats.",
        preferred_styles=["tall-tale", "paper-atlas", "night-file"],
        curiosity_keywords=["heist", "gamble", "millionaire", "soldier", "daring", "escape", "bank"],
        enabled=False,
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
