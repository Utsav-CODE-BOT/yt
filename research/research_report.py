"""Research Report Generator for Autonomous Faceless Shorts Factory.

Formats claim verification records, source citations, and confidence scores
into persistent markdown documentation for auditability.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from research.fact_verifier import FactVerificationSummary
from research.source_collector import SourceRecord


class ResearchReportGenerator:
    """Creates formatted markdown research audit files."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        job_id: str,
        topic_title: str,
        niche: str,
        sources: List[SourceRecord],
        verification_summary: FactVerificationSummary,
    ) -> Path:
        """Write research record to workspace/research/{job_id}_research.md."""
        report_file = self.output_dir / f"{job_id}_research.md"

        status_badge = "PASSED" if verification_summary.passed else "FLAGGED"

        lines = [
            f"# Fact Verification & Research Audit: {job_id}",
            "",
            f"- **Topic**: {topic_title}",
            f"- **Niche**: {niche}",
            f"- **Verification Status**: **{status_badge}**",
            f"- **Confidence Score**: {verification_summary.overall_confidence:.1%}",
            f"- **Total Claims**: {verification_summary.total_claims}",
            f"- **Verified Claims**: {verification_summary.verified_claims}",
            f"- **Unsupported Claims**: {verification_summary.unsupported_claims}",
            "",
            "## 1. Verified Sources & Citations",
            "",
        ]

        for idx, src in enumerate(sources, 1):
            lines.extend([
                f"### Source {idx}: {src.title}",
                f"- **URL**: [{src.url}]({src.url})",
                f"- **Domain Credibility**: {src.credibility_score * 100:.0f}%",
                f"- **Retrieved**: {src.retrieval_date}",
                f"- **Key Evidence Excerpt**: *\"{src.excerpt}\"*",
                "",
            ])

        lines.extend([
            "## 2. Claim-by-Claim Verification Ledger",
            "",
            "| # | Claim Type | Statement | Status | Confidence | Evidence Notes |",
            "|---|---|---|---|---|---|",
        ])

        for idx, res in enumerate(verification_summary.results, 1):
            clean_stmt = res.claim.statement.replace("|", "/")
            lines.append(
                f"| {idx} | `{res.claim.claim_type}` | {clean_stmt} | `{res.status}` | {res.confidence:.1%} | {res.evidence_notes} |"
            )

        lines.extend([
            "",
            "---",
            "*Generated autonomously by Faceless Shorts Factory Research Engine.*",
            "",
        ])

        report_file.write_text("\n".join(lines), encoding="utf-8")
        return report_file
