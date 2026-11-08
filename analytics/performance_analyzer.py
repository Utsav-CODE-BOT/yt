"""Performance Analyzer for Autonomous Faceless Shorts Factory.

Classifies video retention, calculates engagement ratios, and detects hook drop-off.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from analytics.youtube_analytics import VideoPerformanceMetrics

logger = logging.getLogger("factory.analyzer")


@dataclass
class PerformanceEvaluation:
    tier: str  # 'HIGH_PERFORMER', 'STANDARD', 'UNDERPERFORMER'
    hook_retention_healthy: bool
    like_ratio: float
    recommendation: str


class PerformanceAnalyzer:
    """Evaluates video retention curve and overall audience resonance."""

    def evaluate(self, metrics: VideoPerformanceMetrics) -> PerformanceEvaluation:
        apv = metrics.average_view_percentage
        ret_5s = metrics.retention_at_5s
        like_ratio = metrics.likes / max(1, metrics.views)

        hook_healthy = ret_5s >= 70.0

        if apv >= 80.0 and hook_healthy:
            tier = "HIGH_PERFORMER"
            rec = "Niche and style resonance is strong. Prioritize this topic cluster."
        elif apv >= 60.0:
            tier = "STANDARD"
            rec = "Solid performance. Tighten first 2 seconds to boost early retention."
        else:
            tier = "UNDERPERFORMER"
            rec = "Significant early drop-off. Revise hook structure and pacing."

        return PerformanceEvaluation(
            tier=tier,
            hook_retention_healthy=hook_healthy,
            like_ratio=like_ratio,
            recommendation=rec,
        )
