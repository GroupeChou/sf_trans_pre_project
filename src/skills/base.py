"""Base Skill class — All prediction Skills inherit from this."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from src.evidence.blackboard import EvidenceBlackboard
from src.skills.schema import (
    ForecastClaim,
    ForecastTarget,
    ClaimDistribution,
    ClaimDistributionType,
    SkillCategory,
    RiskFlag,
    ExecutionInfo,
)


class BaseSkill(ABC):
    """Abstract base for all prediction Skills in the marketplace."""

    skill_id: str = ""
    name: str = ""
    category: SkillCategory = SkillCategory.CORE_PREDICTION
    version: str = "1.0.0"

    confidence_level: float = 0.85
    avg_mape: float = 0.10
    avg_latency_ms: int = 150

    def __init__(self):
        self._params: dict[str, Any] = {}

    @abstractmethod
    async def execute(
        self,
        target: ForecastTarget,
        blackboard: EvidenceBlackboard,
        **params: Any,
    ) -> ForecastClaim:
        """Execute the Skill and return a ForecastClaim."""

    async def run(
        self,
        target: ForecastTarget,
        blackboard: EvidenceBlackboard,
        **params: Any,
    ) -> ForecastClaim:
        """Run the Skill with timing and error handling."""
        start = time.monotonic()
        try:
            claim = await self.execute(target, blackboard, **params)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return self._error_claim(target, str(exc), duration_ms)

        duration_ms = int((time.monotonic() - start) * 1000)
        claim.execution = ExecutionInfo(
            duration_ms=duration_ms,
            parameters_used=params if params else self.default_params(),
            version=self.version,
        )
        claim.skill_version = self.version
        claim.category = self.category
        return claim

    def default_params(self) -> dict[str, Any]:
        return {}

    def set_params(self, **params: Any) -> None:
        self._params.update(params)

    def _build_claim(
        self,
        target: ForecastTarget,
        mean: float,
        sigma: float | None = None,
        confidence: float | None = None,
        assumptions: list[str] | None = None,
        risk_flags: list[RiskFlag] | None = None,
    ) -> ForecastClaim:
        sigma = sigma or mean * 0.12
        z = 1.28
        return ForecastClaim(
            skill_id=self.skill_id,
            skill_version=self.version,
            category=self.category,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=round(mean, 0),
                p10=round(mean - z * sigma, 0),
                p50=round(mean, 0),
                p90=round(mean + z * sigma, 0),
                sigma=round(sigma, 0),
                confidence=confidence or self.confidence_level,
            ),
            assumptions=assumptions or [],
            risk_flags=risk_flags or [],
        )

    def _error_claim(
        self, target: ForecastTarget, error_msg: str, duration_ms: int
    ) -> ForecastClaim:
        return ForecastClaim(
            skill_id=self.skill_id,
            skill_version=self.version,
            category=self.category,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.POINT,
                mean=0.0,
                confidence=0.0,
            ),
            assumptions=[f"ERROR: {error_msg}"],
            risk_flags=[RiskFlag.DATA_MISSING],
            execution=ExecutionInfo(
                duration_ms=duration_ms,
                parameters_used={"error": error_msg},
                version=self.version,
            ),
        )
