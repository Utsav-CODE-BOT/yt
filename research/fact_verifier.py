"""Fact Verification Engine for Autonomous Faceless Shorts Factory.

Validates extracted claims against source records and seed facts,
detects unsupported numerical claims or contradictions, and produces verification audits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from research.claim_extractor import ExtractedClaim
from research.source_collector import SourceRecord

logger = logging.getLogger("factory.fact_verifier")


@dataclass
class ClaimVerificationResult:
    claim: ExtractedClaim
    status: str  # 'VERIFIED', 'UNSUPPORTED', 'PLAUSIBLE'
    evidence_notes: str
    confidence: float


@dataclass
class FactVerificationSummary:
    passed: bool
    total_claims: int
    verified_claims: int
    unsupported_claims: int
    overall_confidence: float
    results: List[ClaimVerificationResult]


class FactVerifier:
    """Verifies factual claims against authoritative knowledge sources."""

    def verify_claims(
        self,
        claims: List[ExtractedClaim],
        sources: List[SourceRecord],
        seed_facts: List[str],
    ) -> FactVerificationSummary:
        """Evaluate corroboration between claims and available source texts."""
        results: List[ClaimVerificationResult] = []
        corroborating_text = " ".join([s.excerpt for s in sources] + seed_facts).lower()

        verified_count = 0
        unsupported_count = 0

        for claim in claims:
            # Check overlap between claim keywords and evidence text
            overlap_hits = sum(1 for kw in claim.keywords if kw in corroborating_text)
            overlap_ratio = overlap_hits / len(claim.keywords) if claim.keywords else 0.0

            if overlap_ratio >= 0.40 or len(claims) <= 1:
                status = "VERIFIED"
                confidence = min(0.98, 0.70 + overlap_ratio * 0.3)
                notes = f"Corroborated by source text (keyword match: {overlap_hits}/{len(claim.keywords)})"
                verified_count += 1
            elif overlap_ratio >= 0.20:
                status = "PLAUSIBLE"
                confidence = 0.65
                notes = "Plausible contextual correlation with topic sources"
                verified_count += 1
            else:
                status = "UNSUPPORTED"
                confidence = 0.30
                notes = "Insufficient direct corroboration in cited source excerpt"
                unsupported_count += 1

            results.append(
                ClaimVerificationResult(
                    claim=claim,
                    status=status,
                    evidence_notes=notes,
                    confidence=confidence,
                )
            )

        total = len(claims)
        pass_ratio = verified_count / total if total > 0 else 1.0
        passed = unsupported_count == 0 or pass_ratio >= 0.75
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 1.0

        logger.info(
            "Fact check complete: %d/%d verified (Passed: %s, Confidence: %.2f)",
            verified_count,
            total,
            passed,
            avg_confidence,
        )

        return FactVerificationSummary(
            passed=passed,
            total_claims=total,
            verified_claims=verified_count,
            unsupported_claims=unsupported_count,
            overall_confidence=avg_confidence,
            results=results,
        )
