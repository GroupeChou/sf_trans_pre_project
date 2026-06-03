"""publish node — Finalize and publish prediction result (pure code, 0 tokens)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.orchestration.state import ForecastState


async def publish_node(state: ForecastState) -> dict:
    """Publish the final calibrated forecast and record audit trail.

    🟢 Pure code: 0 tokens.
    """
    calibrated = state.get("calibrated", {})
    hitl = state.get("hitl", {})
    difficulty = state.get("difficulty", {})
    selected = state.get("selected_skills", [])
    intent = state.get("intent", {})

    result = {
        "trace_id": state["trace_id"],
        "site_code": intent.get("site_code", ""),
        "target_date": intent.get("target_date", ""),
        "prediction": {
            "mean": calibrated.get("mean"),
            "confidence_interval": [
                calibrated.get("confidence_interval_lower"),
                calibrated.get("confidence_interval_upper"),
            ],
            "p10": calibrated.get("p10"),
            "p50": calibrated.get("p50"),
            "p90": calibrated.get("p90"),
            "consensus_score": calibrated.get("consensus_score"),
        },
        "metadata": {
            "selected_skills": selected,
            "contributing_skills": calibrated.get("contributing_skills", []),
            "difficulty_level": difficulty.get("level", "unknown"),
            "difficulty_score": difficulty.get("score"),
            "requires_hitl": hitl.get("required", False),
            "hitl_reason": hitl.get("reason", ""),
            "execution_path": state.get("execution_path", []),
            "token_used": state.get("token_used", 0),
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    return {"result": result}
