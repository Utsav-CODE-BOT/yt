"""YouTube Metadata Generator for Autonomous Faceless Shorts Factory.

Produces viral titles (<60 chars with #Shorts), informative descriptions with source citations,
and algorithmic tags.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List

from content.llm_client import OllamaClient
from research.source_collector import SourceRecord

logger = logging.getLogger("factory.metadata_generator")


@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: List[str]
    category_id: str  # 27 = Education, 28 = Science & Technology


class MetadataGenerator:
    """Generates optimized metadata complying with YouTube Shorts discovery standards."""

    def __init__(self, llm: Optional[OllamaClient] = None):
        self.llm = llm

    def generate_metadata(
        self,
        topic_title: str,
        niche: str,
        script_text: str,
        hook: str,
        sources: List[SourceRecord],
    ) -> VideoMetadata:
        """Create title, description with citations, and tags."""
        # 1. Title generation: punchy, under 60 chars including #Shorts
        clean_hook = re.sub(r"[.!?]+$", "", hook).strip()
        if len(clean_hook) <= 50:
            title = f"{clean_hook} #Shorts"
        else:
            words = clean_hook.split()
            truncated = " ".join(words[:7])
            title = f"{truncated}... #Shorts"

        # 2. Description generation
        source_lines = []
        for s in sources[:3]:
            source_lines.append(f"- {s.title}: {s.url}")

        desc_paragraphs = [
            f"{clean_hook}.",
            "",
            f"Factual short explainer on {topic_title.lower()} ({niche}).",
            "",
            "Sources & Further Reading:",
            "\n".join(source_lines) if source_lines else "- Authoritative scientific & historical records.",
            "",
            "#Science #Facts #DidYouKnow #Curiosity #Shorts",
        ]
        description = "\n".join(desc_paragraphs)

        # 3. Tags
        base_tags = ["shorts", "facts", "educational", "science", "curiosity"]
        niche_tags = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", niche)]
        tags = list(dict.fromkeys(base_tags + niche_tags))[:10]

        # Category: Education (27)
        category_id = "27"
        if "Technology" in niche or "Space" in niche:
            category_id = "28"

        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
        )
