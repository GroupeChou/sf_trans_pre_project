"""ForecastClaim Schema — Standardized prediction claim format for all Skills."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    CORE_PREDICTION = "core_prediction"
    STATISTICAL = "statistical"
    DIMENSION_SPLIT = "dimension_split"
    VALIDATION = "validation"
    POST_PROCESSING = "post_processing"
    MODEL_BASELINE = "model_baseline"


class ClaimDistributionType(str, Enum):
    NORMAL = "normal"
    LOG_NORMAL = "lognormal"
    POINT = "point"
    EMPIRICAL = "empirical"


class TargetDimension(str, Enum):
    SITE_TOTAL = "site_total"
    SHIFT_LEVEL = "shift_level"
    WAREHOUSE_LEVEL = "warehouse_level"
    COLLECTION_DISTRIBUTION = "collection_distribution"
    ECONOMIC_ZONE = "economic_zone"
    CUSTOMER = "customer"


class RiskFlag(str, Enum):
    HIGH_UNCERTAINTY = "high_uncertainty"
    DATA_MISSING = "data_missing"
    MODEL_ANOMALY = "model_anomaly"
    EXTERNAL_EVENT = "external_event"
    REQUIRES_HITL = "requires_hitl"


class ForecastTarget(BaseModel):
    site_code: str = Field(..., description="Site identifier, e.g., 021WD")
    target_date: str = Field(..., description="Target date in YYYY-MM-DD")
    dimension: TargetDimension = TargetDimension.SITE_TOTAL
    horizon: str = "T+1"


class ClaimDistribution(BaseModel):
    type: ClaimDistributionType = ClaimDistributionType.NORMAL
    mean: float
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    sigma: float | None = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class ExecutionInfo(BaseModel):
    duration_ms: int
    parameters_used: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"


class ForecastClaim(BaseModel):
    schema_version: str = "forecast.claim.v1"
    trace_id: str = Field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:12]}")
    skill_id: str
    skill_version: str = "1.0.0"
    category: SkillCategory

    target: ForecastTarget
    claim: ClaimDistribution
    evidence_refs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    execution: ExecutionInfo | None = None

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FusedForecast(BaseModel):
    trace_id: str
    mean: float
    sigma: float
    p10: float
    p50: float
    p90: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    consensus_score: float = Field(ge=0.0, le=1.0)
    contributing_skills: list[str]
    skill_contributions: dict[str, float] = Field(default_factory=dict)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    difficulty_score: float | None = None
    difficulty_level: str | None = None
    requires_hitl: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
