"""calibrate node — Conformal calibration of prediction intervals (pure stats, 0 tokens)."""

from __future__ import annotations

from src.fusion.conformal import conformal_calibrate
from src.orchestration.state import ForecastState
from src.skills.schema import FusedForecast, RiskFlag


async def calibrate_node(state: ForecastState) -> dict:
    """Apply Conformal Calibration to adjust prediction intervals.

    🟢 Pure statistics: 0 tokens.
    Uses historical residuals bucketed by site_type × event_type × horizon.
    """
    fused_raw = state.get("fused", {})

    if not fused_raw or fused_raw.get("mean", 0) == 0:
        return {"calibrated": fused_raw}

    fused = FusedForecast(**fused_raw)

    bucket_key = _build_bucket_key(state)
    calibrated = conformal_calibrate(fused, bucket_key)

    # Add difficulty info
    difficulty = state.get("difficulty", {})
    if difficulty:
        calibrated.difficulty_score = difficulty.get("score")
        calibrated.difficulty_level = difficulty.get("level")

    return {"calibrated": calibrated.model_dump()}


def _build_bucket_key(state: ForecastState) -> str:
    intent = state.get("intent", {})
    events = intent.get("events", [])
    event_types = sorted(set(e.get("type", "none") for e in events)) if events else ["none"]
    site = intent.get("site_code", "default")
    return f"{site}:{':'.join(event_types)}:T+1"
