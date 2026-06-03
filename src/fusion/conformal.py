"""Conformal Calibration — Calibrate prediction intervals using historical residuals."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from src.skills.schema import FusedForecast


@dataclass
class CalibratedForecast:
    mean: float
    pi_lower: float
    pi_upper: float
    coverage_level: float = 0.80


def conformal_calibrate(
    fused: FusedForecast,
    bucket_key: str = "default",
    alpha: float = 0.20,
) -> FusedForecast:
    """Calibrate the fused forecast prediction intervals using historical residuals.

    Uses conformal prediction: quantile of historical residuals for the given bucket
    to adjust the confidence interval.
    """
    residuals = _load_residuals(bucket_key)

    if len(residuals) == 0:
        q = fused.sigma * 1.5
    else:
        residuals = np.abs(residuals)
        q = float(np.quantile(residuals, 1 - alpha))

    ci_lower = fused.mean - q
    ci_upper = fused.mean + q

    fused.confidence_interval_lower = round(max(0, ci_lower), 0)
    fused.confidence_interval_upper = round(ci_upper, 0)
    fused.p10 = round(fused.mean - q * 0.8, 0)
    fused.p90 = round(fused.mean + q * 0.8, 0)

    return fused


def _load_residuals(bucket_key: str) -> np.ndarray:
    """Load historical residuals for a given bucket (site_type x event_type x horizon).

    In production, reads from DB. Here returns simulated residuals.
    """
    # Simulated residuals for bootstrapping; in production this queries the DB
    rng = np.random.default_rng(hash(bucket_key) % (2**32))
    return rng.normal(0, 0.08, size=50)
