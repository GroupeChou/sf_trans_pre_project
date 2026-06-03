"""quality_gate node — Validate Skill claims against quality thresholds (pure code, 0 tokens)."""

from __future__ import annotations

import numpy as np

from src.orchestration.state import ForecastState, DisagreementInfo


async def quality_gate_node(state: ForecastState) -> dict:
    """Validate the quality of Skill claims and check if debate is needed.

    🟢 Pure code: 0 tokens.
    Computes the Disagreement Index (DI) = std(claims) / mean(claims).
    If DI > 0.20, debate is triggered.
    """
    skill_claims = state.get("skill_claims", [])
    difficulty = state.get("difficulty", {})

    valid_claims = [
        c for c in skill_claims
        if "error" not in c and c.get("claim", {}).get("mean", 0) > 0
    ]

    if len(valid_claims) < 2:
        di = 0.0
        requires_debate = False
    else:
        means = [c["claim"]["mean"] for c in valid_claims]
        mean_val = float(np.mean(means))
        di = float(np.std(means) / (mean_val + 1e-6)) if mean_val > 0 else 0.0
        requires_debate = di > 0.20

    max_rounds = 1 if difficulty.get("level") in ("low", "medium") else 3

    disagreement: DisagreementInfo = {
        "disagreement_index": round(di, 4),
        "requires_debate": requires_debate,
        "max_rounds": max_rounds,
        "claims_before": [
            {
                "skill_id": c.get("skill_id", "unknown"),
                "mean": c.get("claim", {}).get("mean", 0),
                "confidence": c.get("claim", {}).get("confidence", 0),
            }
            for c in valid_claims
        ],
    }

    return {"disagreement": disagreement}
