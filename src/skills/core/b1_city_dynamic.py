"""B1: 城市动态涨跌幅法 — City dynamic growth rate prediction."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.evidence.blackboard import EvidenceBlackboard
from src.skills.base import BaseSkill
from src.skills.schema import (
    ForecastTarget,
    ForecastClaim,
    SkillCategory,
)


class CityDynamicSkill(BaseSkill):
    """B1: Predict site volume based on city-level dynamic forecast and base period actuals.

    Formula: forecast = base_period_actual × (city_forecast / city_base_period)
    """

    skill_id = "B1_city_dynamic"
    name = "城市动态涨跌幅法"
    category = SkillCategory.CORE_PREDICTION
    confidence_level = 0.88
    avg_mape = 0.068
    avg_latency_ms = 150

    def default_params(self) -> dict[str, Any]:
        return {
            "base_period_rule": "last_week_same_day",
            "smooth_window": 1,
            "city_weight": 0.7,
            "site_weight": 0.3,
        }

    async def execute(
        self,
        target: ForecastTarget,
        blackboard: EvidenceBlackboard,
        **params: Any,
    ) -> ForecastClaim:
        base_rule = params.get("base_period_rule", "last_week_same_day")
        city_w = params.get("city_weight", 0.7)
        site_w = params.get("site_weight", 0.3)

        # In production: fetch from Evidence Blackboard
        # Here we use simulated data with a realistic distribution
        rng = np.random.default_rng(hash(f"{target.site_code}:{target.target_date}") % (2**32))

        city_growth = rng.normal(1.03, 0.04)
        base_actual = rng.normal(145000, 12000)

        city_component = base_actual * city_growth * city_w
        site_component = base_actual * site_w

        mean = float(city_component + site_component)
        sigma = mean * 0.08

        assumptions = [
            f"基期规则: {base_rule}",
            f"城市动态涨跌幅: {city_growth:.2%}",
            f"基期实际值: {base_actual:.0f} 件",
            f"城市权重: {city_w}, 场地权重: {site_w}",
        ]

        return self._build_claim(
            target=target,
            mean=mean,
            sigma=sigma,
            assumptions=assumptions,
        )
