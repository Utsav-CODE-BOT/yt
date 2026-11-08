"""Topic Deduplication Engine for Autonomous Faceless Shorts Factory.

Generates deterministic semantic fingerprints to guarantee novel topics and prevent
repetitive content within the configurable deduplication window.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Set

from core.database import Database

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "don", "should", "now"
}


class TopicDeduplicator:
    """Computes semantic topic fingerprints and verifies against historical database."""

    def __init__(self, db: Database, window_days: int = 60):
        self.db = db
        self.window_days = window_days

    @staticmethod
    def generate_fingerprint(title: str, summary: str = "") -> str:
        """Create a normalized deterministic hash of core keywords."""
        combined = f"{title} {summary}".lower()
        # Remove non-alphanumeric characters
        cleaned = re.sub(r"[^a-z0-9\s]", " ", combined)
        tokens = cleaned.split()
        # Filter stopwords and short tokens
        keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
        # Sort distinct keywords for order-independent similarity matching
        unique_sorted = sorted(set(keywords))
        normalized_str = " ".join(unique_sorted)
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()[:16]

    def is_duplicate(self, title: str, summary: str = "") -> bool:
        """Check if topic fingerprint or key tokens collide with recent topics."""
        fp = self.generate_fingerprint(title, summary)
        if self.db.is_fingerprint_used(fp):
            return True

        # Check token overlap with recent topics
        recent = self.db.get_recent_topics(days=self.window_days)
        new_tokens = set(re.sub(r"[^a-z0-9\s]", " ", title.lower()).split()) - STOP_WORDS
        if not new_tokens:
            return False

        for past in recent:
            past_title = past["title"].lower()
            past_tokens = set(re.sub(r"[^a-z0-9\s]", " ", past_title).split()) - STOP_WORDS
            if not past_tokens:
                continue
            # Jaccard similarity index
            intersection = len(new_tokens.intersection(past_tokens))
            union = len(new_tokens.union(past_tokens))
            similarity = intersection / union if union > 0 else 0
            if similarity > 0.65:
                return True

        return False
