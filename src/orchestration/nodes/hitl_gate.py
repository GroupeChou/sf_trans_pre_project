"""hitl_gate node — Human-in-the-loop threshold check (pure code, 0 tokens)."""

from __future__ import annotations

from src.orchestration.state import ForecastState, HITLInfo


async def hitl_gate_node(state: ForecastState) -> dict:
    """Determine if human review is required.

    🟢 Pure threshold comparison: 0 tokens.

    Triggers HITL when:
    - Disagreement index >= 0.50
    - High business impact with medium disagreement (>= 0.35)
    - F6 fallback is the only functioning Skill
    - Data completeness is critical (< 0.30)
    """
    disagreement = state.get("disagreement", {})
    di = disagreement.get("disagreement_index", 0.0)
    difficulty = state.get("difficulty", {})
    evidence_summary = state.get("evidence_summary", {})
    completeness = evidence_summary.get("completeness", 1.0)
    selected = state.get("selected_skills", [])

    requires_hitl = False
    reasons = []

    if di >= 0.50:
        requires_hitl = True
        reasons.append(f"分歧指数过高 (DI={di:.2f} >= 0.50)")

    if di >= 0.35 and difficulty.get("level") in ("high", "extreme"):
        requires_hitl = True
        reasons.append(f"高难度场景下分歧较大 (DI={di:.2f}, 难度={difficulty.get('level')})")

    if completeness < 0.30:
        requires_hitl = True
        reasons.append(f"数据完备度极低 ({completeness:.2f} < 0.30)")

    if selected == ["F6_historical_median"]:
        requires_hitl = True
        reasons.append("仅剩兜底Skill可用，所有正式Skill失效")

    calibrated = state.get("calibrated", {})
    claims_summary = {
        "skill_count": len(state.get("skill_claims", [])),
        "selected_skills": selected,
        "final_mean": calibrated.get("mean"),
        "confidence_interval": [
            calibrated.get("confidence_interval_lower"),
            calibrated.get("confidence_interval_upper"),
        ],
    }

    hitl: HITLInfo = {
        "required": requires_hitl,
        "reason": "; ".join(reasons) if reasons else "无需人工审核",
        "claims_summary": claims_summary,
    }

    return {"hitl": hitl}
