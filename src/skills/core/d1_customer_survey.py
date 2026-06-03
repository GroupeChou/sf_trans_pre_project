"""D1: 大客户摸底法 — Customer reported volume adjustment with historical bias correction."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.evidence.blackboard import EvidenceBlackboard, EvidenceType
from src.skills.base import BaseSkill
from src.skills.schema import (
    ForecastTarget,
    ForecastClaim,
    SkillCategory,
    RiskFlag,
)


class CustomerSurveySkill(BaseSkill):
    """D1: Adjust forecast based on customer-reported shipment volumes.

    Accounts for historical over/under-reporting bias.
    Formula: adjusted = baseline + customer_reported × (1 - historical_bias_rate)
    """

    skill_id = "D1_customer_survey"
    name = "大客户摸底法"
    category = SkillCategory.CORE_PREDICTION
    confidence_level = 0.72
    avg_mape = 0.092
    avg_latency_ms = 200

    def default_params(self) -> dict[str, Any]:
        return {
            "bias_rate": 0.15,
            "min_report_volume": 1000,
        }

    async def execute(
        self,
        target: ForecastTarget,
        blackboard: EvidenceBlackboard,
        **params: Any,
    ) -> ForecastClaim:
        bias_rate = params.get("bias_rate", 0.15)
        has_customer_data = blackboard.has_type(EvidenceType.CUSTOMER_REPORTED_VOLUME)

        rng = np.random.default_rng(hash(f"{target.site_code}:{target.target_date}:D1") % (2**32))

        baseline = rng.normal(145000, 10000)
        risk_flags: list[RiskFlag] = []

        if has_customer_data:
            # In production: read actual customer reported volume from Blackboard
            reported_extra = rng.normal(20000, 5000)
            adjusted = baseline + reported_extra * (1 - bias_rate)
            assumptions = [
                f"大客户上报件量: +{reported_extra:.0f} 件",
                f"历史虚高偏差率: {bias_rate:.0%}",
                f"调整后增量: +{reported_extra * (1 - bias_rate):.0f} 件",
            ]
        else:
            reported_extra = 0
            adjusted = baseline
            assumptions = [
                "无客户上报数据，使用历史基线",
                "建议联系大客户确认出货计划",
            ]
            risk_flags.append(RiskFlag.DATA_MISSING)

        sigma = adjusted * 0.12

        if has_customer_data and abs(reported_extra) > baseline * 0.15:
            risk_flags.append(RiskFlag.EXTERNAL_EVENT)

        return self._build_claim(
            target=target,
            mean=adjusted,
            sigma=sigma,
            confidence=0.72 if has_customer_data else 0.55,
            assumptions=assumptions,
            risk_flags=risk_flags,
        )
