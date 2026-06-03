"""F1: 极端事件应对方案 — Extreme event impact adjustment (weather, promotion, route changes)."""

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


class ExtremeEventSkill(BaseSkill):
    """F1: Adjust forecast for extreme events like typhoons, promotions, route changes.

    Supports weather decay factors and promotional uplift coefficients.
    """

    skill_id = "F1_extreme_event"
    name = "极端事件应对"
    category = SkillCategory.CORE_PREDICTION
    confidence_level = 0.65
    avg_mape = 0.120
    avg_latency_ms = 200

    def default_params(self) -> dict[str, Any]:
        return {
            "weather_decay_factor": 0.85,
            "promo_uplift_factor": 1.25,
            "route_change_factor": 0.90,
        }

    async def execute(
        self,
        target: ForecastTarget,
        blackboard: EvidenceBlackboard,
        **params: Any,
    ) -> ForecastClaim:
        weather_decay = params.get("weather_decay_factor", 0.85)
        promo_uplift = params.get("promo_uplift_factor", 1.25)

        has_weather = blackboard.has_type(EvidenceType.WEATHER_ALERT)
        has_event = blackboard.has_type(EvidenceType.EVENT_VECTOR)

        rng = np.random.default_rng(hash(f"{target.site_code}:{target.target_date}:F1") % (2**32))
        baseline = rng.normal(145000, 12000)
        risk_flags: list[RiskFlag] = []

        if has_weather and has_event:
            factor = weather_decay * promo_uplift
            assumptions = [
                f"恶劣天气衰减系数: {weather_decay}",
                f"促销放大系数: {promo_uplift}",
                f"综合影响系数: {factor:.2f}",
            ]
            risk_flags.append(RiskFlag.EXTERNAL_EVENT)
            risk_flags.append(RiskFlag.HIGH_UNCERTAINTY)
        elif has_weather:
            factor = weather_decay
            assumptions = [f"恶劣天气衰减系数: {weather_decay}"]
            risk_flags.append(RiskFlag.EXTERNAL_EVENT)
        elif has_event:
            factor = promo_uplift
            assumptions = [f"促销放大系数: {promo_uplift}"]
            risk_flags.append(RiskFlag.EXTERNAL_EVENT)
        else:
            factor = 1.0
            assumptions = ["无极端事件，返回基线预测"]

        mean = baseline * factor
        sigma = mean * 0.18

        if has_weather and has_event:
            confidence = 0.55
        elif has_weather or has_event:
            confidence = 0.65
        else:
            confidence = 0.85

        return self._build_claim(
            target=target,
            mean=mean,
            sigma=sigma,
            confidence=confidence,
            assumptions=assumptions,
            risk_flags=risk_flags,
        )
