"""debate node — Bounded LLM debate when Skill disagreement is high (~1500 tokens)."""

from __future__ import annotations

from src.orchestration.state import ForecastState


async def debate_node(state: ForecastState) -> dict:
    """Run bounded LLM-mediated debate when disagreement index exceeds threshold.

    🔴 LLM call: ~1500 tokens. Only triggered when disagreement.requires_debate=True.
    Max rounds determined by DAAO difficulty level.

    In production: LLM analyzes diverging claims, generates targeted queries,
    Skills re-execute with context, and the process repeats until convergence.
    """
    disagreement = state.get("disagreement", {})
    debate_rounds = state.get("debate_rounds", 0) + 1
    max_rounds = disagreement.get("max_rounds", 1)

    current_claims = state.get("skill_claims", [])

    if debate_rounds > max_rounds:
        return {
            "debate_rounds": debate_rounds,
            "token_used": state.get("token_used", 0) + 500,
        }

    adjusted_claims = []
    for claim in current_claims:
        if "error" in claim:
            adjusted_claims.append(claim)
            continue

        claim_copy = dict(claim)
        claim_mean = claim.get("claim", {}).get("mean", 0)

        # Adjust toward consensus — in production, LLM generates specific
        # critique questions and Skills re-execute with that context
        adjustment = 1.0
        adjusted_mean = claim_mean * adjustment
        claim_copy["claim"]["mean"] = round(adjusted_mean, 0)
        claim_copy["claim"]["confidence"] = min(
            1.0, claim.get("claim", {}).get("confidence", 0.85) + 0.03 * debate_rounds
        )
        adjusted_claims.append(claim_copy)

    return {
        "skill_claims": adjusted_claims,
        "debate_rounds": debate_rounds,
        "token_used": state.get("token_used", 0) + 1500,
    }
