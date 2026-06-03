"""Tests for the orchestration layer and pipeline."""

import pytest

from src.orchestration.pipeline import build_prediction_pipeline
from src.orchestration.state import ForecastState


@pytest.fixture
def basic_state():
    return ForecastState(
        trace_id="tr_test_001",
        request={
            "text": "预测明天金山021WD到件量",
            "site": "021WD",
            "date": "2026-06-04",
        },
        intent={},
        evidence={},
        evidence_summary={},
        has_unstructured_event=False,
        difficulty=None,
        selected_skills=[],
        skill_claims=[],
        disagreement=None,
        debate_rounds=0,
        fused=None,
        calibrated=None,
        hitl=None,
        result=None,
        error=None,
        token_used=0,
        execution_path=[],
    )


@pytest.fixture
def event_state():
    return ForecastState(
        trace_id="tr_test_002",
        request={
            "text": "预测明天金山到件量，得物直播，暴雨预警",
            "site": "021WD",
            "date": "2026-06-04",
        },
        intent={},
        evidence={},
        evidence_summary={},
        has_unstructured_event=False,
        difficulty=None,
        selected_skills=[],
        skill_claims=[],
        disagreement=None,
        debate_rounds=0,
        fused=None,
        calibrated=None,
        hitl=None,
        result=None,
        error=None,
        token_used=0,
        execution_path=[],
    )


class TestPredictionPipeline:
    async def test_basic_routine_prediction(self, basic_state):
        pipeline = build_prediction_pipeline()

        result = await pipeline.invoke(dict(basic_state))

        assert result.get("result") is not None
        assert result.get("error") is None
        assert len(result.get("execution_path", [])) > 0
        assert result["result"]["prediction"]["mean"] > 0

    async def test_event_driven_prediction(self, event_state):
        pipeline = build_prediction_pipeline()

        result = await pipeline.invoke(dict(event_state))

        assert result.get("result") is not None
        assert result.get("error") is None
        assert result["result"]["prediction"]["mean"] > 0
        # Token consumption should be higher for event-driven requests
        assert result["result"]["metadata"]["token_used"] > 0

    async def test_pipeline_visualization(self):
        pipeline = build_prediction_pipeline()
        mermaid = pipeline.visualize()

        assert "parse_intent" in mermaid
        assert "build_evidence" in mermaid
        assert "run_skills" in mermaid
        assert "fuse" in mermaid
        assert "calibrate" in mermaid
        assert "publish" in mermaid

    async def test_result_has_required_fields(self, basic_state):
        pipeline = build_prediction_pipeline()
        result = await pipeline.invoke(dict(basic_state))

        r = result["result"]
        assert "trace_id" in r
        assert "prediction" in r
        assert "mean" in r["prediction"]
        assert "confidence_interval" in r["prediction"]
        assert "metadata" in r
        assert "selected_skills" in r["metadata"]
        assert "difficulty_level" in r["metadata"]
        assert "token_used" in r["metadata"]

    async def test_produces_sensible_values(self, basic_state):
        pipeline = build_prediction_pipeline()
        result = await pipeline.invoke(dict(basic_state))

        mean = result["result"]["prediction"]["mean"]
        ci = result["result"]["prediction"]["confidence_interval"]

        assert 50000 < mean < 300000  # Reasonable volume range
        assert ci[0] <= mean <= ci[1]
        assert result["result"]["prediction"]["consensus_score"] >= 0.0
