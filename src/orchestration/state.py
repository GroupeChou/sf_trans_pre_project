"""ForecastState — TypedDict state flowing through the prediction pipeline."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from src.skills.schema import ForecastClaim, FusedForecast


class DifficultyInfo(TypedDict):
    score: float
    level: str
    factors: dict[str, float]


class DisagreementInfo(TypedDict):
    disagreement_index: float
    requires_debate: bool
    max_rounds: int
    claims_before: list[dict]


class HITLInfo(TypedDict):
    required: bool
    reason: str
    claims_summary: dict[str, Any]


class ForecastState(TypedDict):
    trace_id: str
    request: dict[str, Any]
    intent: dict[str, Any]
    evidence: dict[str, Any]
    evidence_summary: dict[str, Any]
    has_unstructured_event: bool
    difficulty: DifficultyInfo | None
    selected_skills: list[str]
    skill_claims: list[dict[str, Any]]
    disagreement: DisagreementInfo | None
    debate_rounds: int
    fused: dict[str, Any] | None
    calibrated: dict[str, Any] | None
    hitl: HITLInfo | None
    result: dict[str, Any] | None
    error: str | None
    token_used: int
    execution_path: list[str]
