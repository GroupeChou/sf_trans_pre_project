"""Bayesian precision-weighted fusion of multiple Skill claims."""

from __future__ import annotations

import math
import numpy as np

from src.skills.schema import ClaimDistributionType, ForecastClaim, FusedForecast, RiskFlag


def bayesian_fusion(claims: list[ForecastClaim], tau: float = 10.0) -> FusedForecast:
    """Bayesian precision-weighted fusion of multiple ForecastClaims.

    Each Skill's historical reliability (inverse MAPE) acts as precision weight.
    """
    if not claims:
        raise ValueError("At least one claim required for fusion")

    if len(claims) == 1:
        c = claims[0]
        return FusedForecast(
            trace_id=c.trace_id,
            mean=c.claim.mean,
            sigma=c.claim.sigma or c.claim.mean * 0.15,
            p10=c.claim.p10 or c.claim.mean * 0.85,
            p50=c.claim.p50 or c.claim.mean,
            p90=c.claim.p90 or c.claim.mean * 1.15,
            confidence_interval_lower=c.claim.p10 or c.claim.mean * 0.85,
            confidence_interval_upper=c.claim.p90 or c.claim.mean * 1.15,
            consensus_score=1.0,
            contributing_skills=[c.skill_id],
            risk_flags=list(c.risk_flags),
        )

    mus = []
    sigmas = []
    confidences = []
    skill_ids = []

    for claim in claims:
        mu = claim.claim.mean
        sigma = claim.claim.sigma or mu * 0.15
        confidence = claim.claim.confidence

        mus.append(mu)
        sigmas.append(sigma)
        confidences.append(confidence)
        skill_ids.append(claim.skill_id)

    mus = np.array(mus)
    sigmas = np.array(sigmas)
    confidences = np.array(confidences)

    reliability = np.exp(-sigmas / (mus * tau))
    precisions = reliability * confidences / (sigmas ** 2)

    total_precision = np.sum(precisions)
    weights = precisions / total_precision
    mu_fused = float(np.sum(weights * mus))

    variance_fused = 1.0 / total_precision
    sigma_fused = float(math.sqrt(variance_fused + np.var(mus)))

    z_score = 1.28
    ci_lower = mu_fused - z_score * sigma_fused
    ci_upper = mu_fused + z_score * sigma_fused

    consensus = 1.0 - min(1.0, float(np.std(mus) / (np.mean(mus) + 1e-6)))

    all_risk_flags: list[RiskFlag] = []
    for claim in claims:
        for flag in claim.risk_flags:
            if flag not in all_risk_flags:
                all_risk_flags.append(flag)

    skill_contributions = {
        sid: float(w) for sid, w in zip(skill_ids, weights)
    }

    return FusedForecast(
        trace_id=claims[0].trace_id,
        mean=round(mu_fused, 0),
        sigma=round(sigma_fused, 0),
        p10=round(mu_fused - z_score * sigma_fused, 0),
        p50=round(mu_fused, 0),
        p90=round(mu_fused + z_score * sigma_fused, 0),
        confidence_interval_lower=round(ci_lower, 0),
        confidence_interval_upper=round(ci_upper, 0),
        consensus_score=round(consensus, 3),
        contributing_skills=skill_ids,
        skill_contributions=skill_contributions,
        risk_flags=list(set(all_risk_flags)),
    )
