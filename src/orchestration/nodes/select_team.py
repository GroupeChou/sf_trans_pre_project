"""select_team node — Dynamic Skill team selection (Thompson Sampling, pure code)."""

from __future__ import annotations

import hashlib

from src.orchestration.state import ForecastState


async def select_team_node(state: ForecastState) -> dict:
    """Select which Skills to use based on intent, events, and difficulty.

    🟢 Pure code: 0 tokens. Uses DAAO difficulty level to determine team size,
    then falls back to rule-based selection (Thompson Sampling after cold start).
    """
    intent = state.get("intent", {})
    difficulty = state.get("difficulty", {})
    difficulty_level = difficulty.get("level", "medium")
    events = intent.get("events", [])
    event_types = {e.get("type") for e in events}

    all_candidates: list[str] = []

    # Always include the safety net
    all_candidates.append("F6_historical_median")

    # Core prediction skills
    all_candidates.append("B1_city_dynamic")

    # Event-driven skills
    if event_types & {"promotion", "live_stream", "new_customer", "charter_flight"}:
        all_candidates.append("D1_customer_survey")

    if event_types & {"typhoon", "rainstorm", "snowstorm", "fog", "promotion", "live_stream"}:
        all_candidates.append("F1_extreme_event")

    if event_types & {"diversion", "shift_close"}:
        all_candidates.append("G2_diversion_management")

    # Cross-validation for high-difficulty cases
    if difficulty_level in ("high", "extreme"):
        all_candidates.append("H1_cross_validation")

    # Determine team size based on difficulty
    size_map = {"low": 2, "medium": 4, "high": 6, "extreme": 6}
    max_size = size_map.get(difficulty_level, 4)

    selected = all_candidates[:max_size]

    return {"selected_skills": selected}
