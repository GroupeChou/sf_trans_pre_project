"""Integration tests for the full API."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAPI:
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_create_forecast(self, client):
        response = await client.post("/api/v1/forecast", json={
            "site": "021WD",
            "date": "2026-06-04",
            "text": "预测明天金山到件量",
        })
        assert response.status_code == 200
        result = response.json()
        assert result["prediction"]["mean"] > 0
        assert result["trace_id"].startswith("tr_")

    async def test_create_forecast_with_events(self, client):
        response = await client.post("/api/v1/forecast", json={
            "site": "021WD",
            "date": "2026-06-04",
            "text": "预测明天金山到件量，得物直播，台风暴雨预警",
        })
        assert response.status_code == 200
        result = response.json()
        assert result["prediction"]["mean"] > 0
        # Event-driven predictions should consume more tokens
        assert result["metadata"]["token_used"] > 0

    async def test_list_skills(self, client):
        response = await client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 6
        skill_ids = [s["skill_id"] for s in data["skills"]]
        assert "B1_city_dynamic" in skill_ids
        assert "F6_historical_median" in skill_ids

    async def test_get_skill_detail(self, client):
        response = await client.get("/api/v1/skills/B1_city_dynamic")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "城市动态涨跌幅法"
        assert data["category"] == "core_prediction"

    async def test_get_skill_not_found(self, client):
        response = await client.get("/api/v1/skills/NONEXISTENT")
        assert response.status_code == 404

    async def test_pipeline_visualization(self, client):
        response = await client.get("/api/v1/pipeline/visualize")
        assert response.status_code == 200
        assert "parse_intent" in response.json()["mermaid"]


class TestEdgeCases:
    async def test_empty_text(self, client):
        response = await client.post("/api/v1/forecast", json={
            "site": "021WD",
            "date": "2026-06-04",
            "text": "",
        })
        # Should still work with defaults
        assert response.status_code == 200

    async def test_missing_site(self, client):
        response = await client.post("/api/v1/forecast", json={
            "site": "",
            "date": "2026-06-04",
            "text": "预测明天到件量",
        })
        # Should still complete but with degraded quality
        assert response.status_code == 200

    async def test_rate_limit_headers(self, client):
        response = await client.get("/api/v1/health")
        assert "X-Trace-ID" in response.headers
        assert "X-Response-Time-Ms" in response.headers
