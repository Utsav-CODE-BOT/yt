"""Claim Extraction Engine for Autonomous Faceless Shorts Factory.

Parses topic candidates and scripts to extract atomic verifiable claims:
numerical values, scientific mechanisms, dates, names, and assertions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class ExtractedClaim:
    statement: str
    claim_type: str  # 'numerical', 'historical', 'scientific', 'entity'
    keywords: List[str]


class ClaimExtractor:
    """Extracts factual assertions requiring evidence validation."""

    def extract_claims(self, text: str, title: str = "") -> List[ExtractedClaim]:
        """Parse text and extract testable factual statements."""
        claims: List[ExtractedClaim] = []
        full_text = f"{title}. {text}" if title else text
        sentences = [s.strip() for s in re.split(r"[.!?]+", full_text) if len(s.strip()) > 15]

        for sentence in sentences:
            # Check for numerical / statistical claims
            if re.search(r"\b\d+[\d,.]*\b|\b(percent|mph|hours|days|weeks|litres|miles|tonnes|degrees)\b", sentence, re.I):
                words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", sentence)]
                claims.append(
                    ExtractedClaim(
                        statement=sentence,
                        claim_type="numerical",
                        keywords=words[:6],
                    )
                )
            # Check for historical or named entity claims
            elif re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b|\b(king|queen|emperor|army|war|bank|museum)\b", sentence, re.I):
                words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", sentence)]
                claims.append(
                    ExtractedClaim(
                        statement=sentence,
                        claim_type="historical",
                        keywords=words[:6],
                    )
                )
            # General scientific / physiological claims
            else:
                words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", sentence)]
                claims.append(
                    ExtractedClaim(
                        statement=sentence,
                        claim_type="scientific",
                        keywords=words[:6],
                    )
                )

        return claims
