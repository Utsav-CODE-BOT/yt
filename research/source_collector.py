"""Source Collection and Credibility Engine for Autonomous Faceless Shorts Factory.

Maintains trusted academic, institutional, and historical domain rankings,
validates source credibility, and records source citations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger("factory.source_collector")

AUTHORITATIVE_DOMAINS = {
    "nih.gov": 1.0,
    "pubmed.ncbi.nlm.nih.gov": 1.0,
    "nasa.gov": 1.0,
    "smithsonianmag.com": 0.95,
    "britannica.com": 0.95,
    "nature.com": 1.0,
    "science.org": 1.0,
    "scientificamerican.com": 0.90,
    "bbc.com": 0.90,
    "theguardian.com": 0.85,
    "louvre.fr": 0.95,
    "rsc.org": 0.95,
    "mit.edu": 1.0,
    "apa.org": 0.95,
    "redcross.org": 0.95,
    "acsm.org": 0.95,
    "ieee.org": 0.95,
    "amnh.org": 0.95,
    "wikipedia.org": 0.80,
}


@dataclass
class SourceRecord:
    url: str
    title: str
    excerpt: str
    credibility_score: float
    retrieval_date: str


class SourceCollector:
    """Collects and validates citation sources."""

    def evaluate_url_credibility(self, url: str) -> float:
        """Score domain credibility between 0.0 and 1.0."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            for trusted, score in AUTHORITATIVE_DOMAINS.items():
                if domain == trusted or domain.endswith("." + trusted):
                    return score

            if domain.endswith(".gov") or domain.endswith(".edu"):
                return 0.95
            if domain.endswith(".org"):
                return 0.75
            return 0.60
        except Exception:
            return 0.50

    def create_source_record(self, url: str, title: str, excerpt: str) -> SourceRecord:
        """Instantiate a validated source record."""
        credibility = self.evaluate_url_credibility(url)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return SourceRecord(
            url=url,
            title=title,
            excerpt=excerpt[:300],
            credibility_score=credibility,
            retrieval_date=now_str,
        )
