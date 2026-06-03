"""fuse node — Bayesian precision-weighted fusion (pure math, 0 tokens)."""

from __future__ import annotations

from src.fusion.bayesian import bayesian_fusion
from src.orchestration.state import ForecastState
from src.skills.schema import (
    ForecastClaim,
    ForecastTarget,
    ClaimDistribution,
    ClaimDistributionType,
    SkillCategory,
    RiskFlag,
    TargetDimension,
)


async def fuse_node(state: ForecastState) -> dict:
    """Fuse multiple Skill claims using Bayesian precision-weighted fusion.

    🟢 Pure math: 0 tokens.
    """
    skill_claims_raw = state.get("skill_claims", [])

    claims = []
    for raw in skill_claims_raw:
        if "error" in raw:
            continue
        try:
            claim = _reconstruct_claim(raw)
            claims.append(claim)
        except Exception:
            continue

    if not claims:
        return {
            "fused": _empty_fused(state["trace_id"]).model_dump(),
        }

    fused = bayesian_fusion(claims)
    return {"fused": fused.model_dump()}


def _reconstruct_claim(raw: dict) -> ForecastClaim:
    return ForecastClaim(
        trace_id=raw.get("trace_id", ""),
        skill_id=raw.get("skill_id", "unknown"),
        skill_version=raw.get("skill_version", "1.0.0"),
        category=SkillCategory(raw.get("category", "core_prediction")),
        target=ForecastTarget(
            site_code=raw.get("target", {}).get("site_code", ""),
            target_date=raw.get("target", {}).get("target_date", ""),
            dimension=TargetDimension(raw.get("target", {}).get("dimension", "site_total")),
            horizon=raw.get("target", {}).get("horizon", "T+1"),
        ),
        claim=ClaimDistribution(
            type=ClaimDistributionType(raw.get("claim", {}).get("type", "normal")),
            mean=raw.get("claim", {}).get("mean", 0),
            p10=raw.get("claim", {}).get("p10"),
            p50=raw.get("claim", {}).get("p50"),
            p90=raw.get("claim", {}).get("p90"),
            sigma=raw.get("claim", {}).get("sigma"),
            confidence=raw.get("claim", {}).get("confidence", 0.85),
        ),
        evidence_refs=raw.get("evidence_refs", []),
        assumptions=raw.get("assumptions", []),
        risk_flags=[RiskFlag(f) for f in raw.get("risk_flags", [])],
    )


def _empty_fused(trace_id: str):
    from src.skills.schema import FusedForecast
    return FusedForecast(
        trace_id=trace_id,
        mean=0,
        sigma=0,
        p10=0, p50=0, p90=0,
        confidence_interval_lower=0,
        confidence_interval_upper=0,
        consensus_score=0,
        contributing_skills=[],
    )
