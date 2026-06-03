"""Tests for the 6 core prediction Skills."""

import pytest

from src.evidence.blackboard import EvidenceBlackboard, EvidenceEntry, EvidenceType
from src.skills.core.b1_city_dynamic import CityDynamicSkill
from src.skills.core.d1_customer_survey import CustomerSurveySkill
from src.skills.core.f1_extreme_event import ExtremeEventSkill
from src.skills.core.g2_diversion import DiversionManagementSkill
from src.skills.core.h1_cross_validation import CrossValidationSkill
from src.skills.core.f6_fallback import FallbackSkill
from src.skills.schema import ForecastTarget, TargetDimension, RiskFlag


@pytest.fixture
def target():
    return ForecastTarget(
        site_code="021WD",
        target_date="2026-06-04",
        dimension=TargetDimension.SITE_TOTAL,
    )


@pytest.fixture
def blackboard():
    bb = EvidenceBlackboard("tr_test_001")
    bb.add(EvidenceEntry(
        type=EvidenceType.TIMESERIES_VOLUME,
        source="test",
        content_ref="timeseries:021WD:2026-06-04:30d",
        quality_score=0.95,
    ))
    return bb


class TestCityDynamicSkill:
    async def test_basic_prediction(self, target, blackboard):
        skill = CityDynamicSkill()
        claim = await skill.run(target, blackboard)

        assert claim.skill_id == "B1_city_dynamic"
        assert claim.claim.mean > 0
        assert claim.claim.confidence > 0
        assert claim.execution is not None
        assert claim.execution.duration_ms >= 0

    async def test_with_params(self, target, blackboard):
        skill = CityDynamicSkill()
        claim = await skill.run(target, blackboard, city_weight=0.8, site_weight=0.2)

        assert claim.claim.mean > 0
        assert "城市权重: 0.8" in str(claim.assumptions)


class TestCustomerSurveySkill:
    async def test_without_customer_data(self, target, blackboard):
        skill = CustomerSurveySkill()
        claim = await skill.run(target, blackboard)

        assert claim.skill_id == "D1_customer_survey"
        assert RiskFlag.DATA_MISSING in claim.risk_flags
        assert claim.claim.confidence <= 0.55

    async def test_with_customer_data(self, target, blackboard):
        blackboard.add(EvidenceEntry(
            type=EvidenceType.CUSTOMER_REPORTED_VOLUME,
            source="kadm",
            content_ref="customer_report:021WD",
            quality_score=0.75,
        ))
        skill = CustomerSurveySkill()
        claim = await skill.run(target, blackboard)

        assert claim.claim.mean > 0
        assert claim.claim.confidence >= 0.70
        assert "大客户上报件量" in str(claim.assumptions)


class TestExtremeEventSkill:
    async def test_no_events(self, target, blackboard):
        skill = ExtremeEventSkill()
        claim = await skill.run(target, blackboard)

        assert claim.claim.confidence >= 0.80
        assert "无极端事件" in str(claim.assumptions)

    async def test_with_weather(self, target, blackboard):
        blackboard.add(EvidenceEntry(
            type=EvidenceType.WEATHER_ALERT,
            source="weather_api",
            content_ref="weather:021WD",
            quality_score=0.85,
        ))
        skill = ExtremeEventSkill()
        claim = await skill.run(target, blackboard)

        assert RiskFlag.EXTERNAL_EVENT in claim.risk_flags
        assert "恶劣天气衰减系数" in str(claim.assumptions)


class TestDiversionSkill:
    async def test_basic(self, target, blackboard):
        skill = DiversionManagementSkill()
        claim = await skill.run(target, blackboard)

        assert claim.skill_id == "G2_diversion_management"
        assert claim.claim.mean > 0

    async def test_with_diversion_data(self, target, blackboard):
        blackboard.add(EvidenceEntry(
            type=EvidenceType.DIVERSION_RECORD,
            source="satis",
            content_ref="diversion:021WD",
            quality_score=0.70,
        ))
        skill = DiversionManagementSkill()
        claim = await skill.run(target, blackboard)

        assert "倒货" in str(claim.assumptions)


class TestCrossValidationSkill:
    async def test_basic(self, target, blackboard):
        skill = CrossValidationSkill()
        claim = await skill.run(target, blackboard)

        assert claim.skill_id == "H1_cross_validation"
        assert "变异系数" in str(claim.assumptions)


class TestFallbackSkill:
    async def test_always_returns_value(self, target, blackboard):
        skill = FallbackSkill()
        claim = await skill.run(target, blackboard)

        assert claim.skill_id == "F6_historical_median"
        assert RiskFlag.HIGH_UNCERTAINTY in claim.risk_flags
        assert RiskFlag.REQUIRES_HITL in claim.risk_flags
        assert claim.claim.confidence <= 0.40
        assert "兜底预测" in str(claim.assumptions)
