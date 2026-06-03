"""HITL Gateway — Threshold-based routing to human review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HITLDecision:
    required: bool
    reason: str
    session_id: str | None = None
    escalation_level: str = "none"


class HITLGateway:
    """Gateway that routes high-risk predictions to human review.

    Escalation levels:
    - none: DI < 0.35, auto-publish
    - notify: 0.35 ≤ DI < 0.50, publish with warning
    - review: DI ≥ 0.50 or high-impact, require human review
    - critical: completeness < 0.30 or only F6 available, escalate immediately
    """

    def evaluate(
        self,
        trace_id: str,
        disagreement_index: float,
        difficulty_level: str,
        completeness: float,
        selected_skills: list[str],
        business_impact: str = "normal",
    ) -> HITLDecision:
        if completeness < 0.30:
            return HITLDecision(
                required=True,
                reason=f"数据完备度极低 ({completeness:.0%})，建议人工决策",
                escalation_level="critical",
            )

        if selected_skills == ["F6_historical_median"]:
            return HITLDecision(
                required=True,
                reason="所有正式Skill失效，仅剩兜底值，需人工确认",
                escalation_level="critical",
            )

        if disagreement_index >= 0.50:
            return HITLDecision(
                required=True,
                reason=f"Skill分歧指数过高 ({disagreement_index:.2f})，需人工仲裁",
                session_id=f"hitl_{trace_id}",
                escalation_level="review",
            )

        if disagreement_index >= 0.35 and business_impact == "high":
            return HITLDecision(
                required=True,
                reason=f"高业务影响下分歧较大 ({disagreement_index:.2f})",
                session_id=f"hitl_{trace_id}",
                escalation_level="review",
            )

        if disagreement_index >= 0.35:
            return HITLDecision(
                required=False,
                reason=f"分歧中等 ({disagreement_index:.2f})，已自动消解但建议关注",
                escalation_level="notify",
            )

        return HITLDecision(
            required=False,
            reason="共识度高，自动发布",
            escalation_level="none",
        )
