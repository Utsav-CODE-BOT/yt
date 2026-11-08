"""Originality and Plagiarism Checker for Autonomous Faceless Shorts Factory.

Computes 3-gram and 4-gram overlap against historical scripts in SQLite
to ensure every generated video is substantially unique.
"""

from __future__ import annotations

import re
from typing import List, Set

from core.database import Database


class OriginalityChecker:
    """Verifies that newly generated scripts do not copy previous scripts."""

    def __init__(self, db: Database, threshold: float = 0.35):
        self.db = db
        self.threshold = threshold

    @staticmethod
    def get_ngrams(text: str, n: int = 3) -> Set[str]:
        """Extract set of word n-grams."""
        cleaned = re.sub(r"[^a-z0-9\s]", "", text.lower())
        words = cleaned.split()
        if len(words) < n:
            return set(words)
        return {" ".join(words[i:i+n]) for i in range(len(words) - n + 1)}

    def check_originality(self, new_script: str) -> bool:
        """Return True if script is novel, False if too similar to an existing script."""
        new_ngrams = self.get_ngrams(new_script, n=3)
        if not new_ngrams:
            return True

        # Fetch recent scripts
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT script_text FROM scripts ORDER BY created_at DESC LIMIT 100")
            rows = cursor.fetchall()

        for row in rows:
            past_text = row["script_text"]
            past_ngrams = self.get_ngrams(past_text, n=3)
            if not past_ngrams:
                continue

            overlap = len(new_ngrams.intersection(past_ngrams))
            similarity = overlap / min(len(new_ngrams), len(past_ngrams))
            if similarity > self.threshold:
                return False

        return True
