"""score_difficulty node — DAAO difficulty scoring (pure code, 0 tokens)."""

from __future__ import annotations

from src.orchestration.state import ForecastState, DifficultyInfo


async def score_difficulty_node(state: ForecastState) -> dict:
    """Score prediction difficulty using DAAO-inspired 4-factor model.

    🟢 Pure computation: 0 tokens.

    Difficulty = 0.30×(1-data_completeness) + 0.25×event_complexity
               + 0.25×site_volatility + 0.20×case_rarity
    """
    evidence_summary = state.get("evidence_summary", {})
    intent = state.get("intent", {})
    events = intent.get("events", [])

    completeness = evidence_summary.get("completeness", 0.85)

    event_count = len(events)
    if event_count == 0:
        event_complexity = 0.0
    elif event_count <= 2:
        event_types = {e.get("type") for e in events}
        event_complexity = 0.3 if len(event_types) == 1 else 0.5
    else:
        event_complexity = 1.0

    # In production: read from site profile DB. Here use reasonable default.
    site_volatility = 0.25

    # Rarity: fewer historical cases = higher difficulty
    # In production: query historical case count
    case_rarity = 0.30

    score = (
        0.30 * (1 - completeness)
        + 0.25 * event_complexity
        + 0.25 * site_volatility
        + 0.20 * case_rarity
    )

    score = round(score, 2)

    if score < 0.30:
        level = "low"
    elif score < 0.55:
        level = "medium"
    elif score < 0.75:
        level = "high"
    else:
        level = "extreme"

    difficulty: DifficultyInfo = {
        "score": score,
        "level": level,
        "factors": {
            "data_incompleteness": round(1 - completeness, 2),
            "event_complexity": event_complexity,
            "site_volatility": site_volatility,
            "case_rarity": case_rarity,
        },
    }

    return {"difficulty": difficulty}
