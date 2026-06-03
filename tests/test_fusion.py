"""Tests for Bayesian fusion, Conformal calibration, and Thompson Sampling."""

import pytest

from src.skills.schema import (
    ForecastClaim,
    ForecastTarget,
    ClaimDistribution,
    ClaimDistributionType,
    SkillCategory,
    TargetDimension,
)
from src.fusion.bayesian import bayesian_fusion
from src.fusion.conformal import conformal_calibrate
from src.fusion.thompson import ThompsonSampler


@pytest.fixture
def sample_claims():
    target = ForecastTarget(
        site_code="021WD",
        target_date="2026-06-04",
        dimension=TargetDimension.SITE_TOTAL,
    )
    return [
        ForecastClaim(
            trace_id="tr_001",
            skill_id="B1_city_dynamic",
            category=SkillCategory.CORE_PREDICTION,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=152000,
                sigma=12000,
                p10=137000,
                p90=167000,
                confidence=0.88,
            ),
        ),
        ForecastClaim(
            trace_id="tr_001",
            skill_id="D1_customer_survey",
            category=SkillCategory.CORE_PREDICTION,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=168000,
                sigma=15000,
                p10=149000,
                p90=187000,
                confidence=0.72,
            ),
        ),
        ForecastClaim(
            trace_id="tr_001",
            skill_id="F6_historical_median",
            category=SkillCategory.CORE_PREDICTION,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=145000,
                sigma=20000,
                p10=120000,
                p90=170000,
                confidence=0.40,
            ),
        ),
    ]


class TestBayesianFusion:
    def test_fuses_multiple_claims(self, sample_claims):
        result = bayesian_fusion(sample_claims)
        assert result.mean > 0
        assert result.sigma > 0
        assert result.confidence_interval_lower < result.mean < result.confidence_interval_upper
        assert 0.0 <= result.consensus_score <= 1.0
        assert len(result.contributing_skills) == 3

    def test_single_claim(self, sample_claims):
        result = bayesian_fusion(sample_claims[:1])
        assert result.mean == sample_claims[0].claim.mean
        assert result.consensus_score == 1.0

    def test_empty_claims_raises(self):
        with pytest.raises(ValueError):
            bayesian_fusion([])

    def test_higher_confidence_claims_weight_more(self):
        target = ForecastTarget(
            site_code="021WD",
            target_date="2026-06-04",
        )
        high_conf = ForecastClaim(
            trace_id="tr_001",
            skill_id="high",
            category=SkillCategory.CORE_PREDICTION,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=150000, sigma=5000, confidence=0.95,
            ),
        )
        low_conf = ForecastClaim(
            trace_id="tr_001",
            skill_id="low",
            category=SkillCategory.CORE_PREDICTION,
            target=target,
            claim=ClaimDistribution(
                type=ClaimDistributionType.NORMAL,
                mean=160000, sigma=20000, confidence=0.40,
            ),
        )
        result = bayesian_fusion([high_conf, low_conf])
        assert abs(result.mean - 150000) < abs(result.mean - 160000)


class TestConformalCalibration:
    def test_calibrates_intervals(self, sample_claims):
        fused = bayesian_fusion(sample_claims)
        original_lower = fused.confidence_interval_lower
        calibrated = conformal_calibrate(fused, "021WD:default:T+1")
        assert calibrated.confidence_interval_lower > 0
        assert calibrated.confidence_interval_upper >= calibrated.confidence_interval_lower

    def test_produces_valid_intervals(self, sample_claims):
        fused = bayesian_fusion(sample_claims)
        calibrated = conformal_calibrate(fused, "test_bucket", alpha=0.20)
        assert calibrated.p10 <= calibrated.p50 <= calibrated.p90


class TestThompsonSampler:
    def test_select_skills_cold_start(self):
        sampler = ThompsonSampler()
        skills = sampler.select_skills(
            bucket="021WD:routine:T+1",
            candidate_skills=["B1", "D1", "F1", "G2", "H1", "F6"],
            n_select=3,
        )
        assert len(skills) == 3
        assert all(isinstance(s[1], float) for s in skills)

    def test_update_improves_posterior(self):
        sampler = ThompsonSampler()

        for _ in range(50):
            sampler.update("B1", "021WD:routine:T+1", reward=0.92)

        post = sampler.get_posterior("B1", "021WD:routine:T+1")
        assert post.mu > 0.8
        assert post.n == 50

    def test_different_buckets_independent(self):
        sampler = ThompsonSampler()

        sampler.update("B1", "bucket_A", reward=0.95)
        sampler.update("B1", "bucket_B", reward=0.50)

        post_a = sampler.get_posterior("B1", "bucket_A")
        post_b = sampler.get_posterior("B1", "bucket_B")
        assert post_a.mu != post_b.mu
