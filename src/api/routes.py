"""API routes — FastAPI endpoints for the prediction platform."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.orchestration.pipeline import build_prediction_pipeline
from src.orchestration.state import ForecastState

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@router.post("/forecast")
async def create_forecast(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """Create a new prediction request.

    Request body:
    {
        "site": "021WD",             // Site code (required)
        "date": "2026-06-04",       // Target date (optional, defaults to T+1)
        "text": "预测明天金山到件量，得物直播，暴雨预警"  // Natural language request
    }
    """
    trace_id = getattr(request.state, "trace_id", f"tr_{uuid.uuid4().hex[:12]}")

    initial_state: ForecastState = {
        "trace_id": trace_id,
        "request": {
            "text": body.get("text", ""),
            "site": body.get("site", ""),
            "date": body.get("date", ""),
        },
        "intent": {},
        "evidence": {},
        "evidence_summary": {},
        "has_unstructured_event": False,
        "difficulty": None,
        "selected_skills": [],
        "skill_claims": [],
        "disagreement": None,
        "debate_rounds": 0,
        "fused": None,
        "calibrated": None,
        "hitl": None,
        "result": None,
        "error": None,
        "token_used": 0,
        "execution_path": [],
    }

    pipeline = build_prediction_pipeline()
    result_state = await pipeline.invoke(initial_state)

    if result_state.get("error"):
        raise HTTPException(status_code=500, detail=result_state["error"])

    return result_state.get("result", {"error": "No result produced"})


@router.get("/forecast/{trace_id}")
async def get_forecast(trace_id: str) -> dict[str, Any]:
    """Retrieve an existing forecast by trace_id."""
    # In production: read from DB
    return {"trace_id": trace_id, "status": "not_found", "message": "Audit DB not yet connected"}


@router.get("/skills")
async def list_skills(category: str | None = None) -> dict[str, Any]:
    """List all available prediction Skills."""
    from src.skills.registry import SkillRegistry
    from src.skills.schema import SkillCategory

    registry = SkillRegistry()
    _register_skills(registry)

    cat = SkillCategory(category) if category else None
    skills = registry.list_published(cat)

    result = []
    for sid in skills:
        meta = registry.get_metadata(sid)
        if meta:
            result.append({
                "skill_id": meta.skill_id,
                "name": meta.name,
                "category": meta.category.value,
                "version": meta.version,
                "avg_mape": meta.avg_mape,
                "avg_latency_ms": meta.avg_latency_ms,
                "status": registry.get_status(sid),
            })

    return {"skills": result, "total": len(result)}


@router.get("/skills/{skill_id}")
async def get_skill_detail(skill_id: str) -> dict[str, Any]:
    """Get detailed information about a specific Skill."""
    from src.skills.registry import SkillRegistry

    registry = SkillRegistry()
    _register_skills(registry)

    meta = registry.get_metadata(skill_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")

    return {
        "skill_id": meta.skill_id,
        "name": meta.name,
        "category": meta.category.value,
        "version": meta.version,
        "description": meta.description,
        "required_evidence": meta.required_evidence,
        "optional_evidence": meta.optional_evidence,
        "recommended_scenarios": meta.recommended_scenarios,
        "not_recommended_for": meta.not_recommended_for,
        "avg_mape": meta.avg_mape,
        "avg_latency_ms": meta.avg_latency_ms,
        "priority": meta.priority,
        "status": registry.get_status(skill_id),
    }


@router.get("/pipeline/visualize")
async def visualize_pipeline() -> dict[str, str]:
    """Return Mermaid visualization of the prediction pipeline."""
    pipeline = build_prediction_pipeline()
    return {"mermaid": pipeline.visualize()}


@router.post("/admin/skills/register")
async def register_skill(body: dict[str, Any]) -> dict[str, Any]:
    """Admin endpoint: Register a new Skill (placeholder)."""
    return {"status": "registered", "skill_id": body.get("skill_id", "unknown")}


@router.post("/admin/skills/{skill_id}/deprecate")
async def deprecate_skill(skill_id: str) -> dict[str, Any]:
    """Admin endpoint: Deprecate a Skill."""
    return {"status": "deprecated", "skill_id": skill_id}


def _register_skills(registry) -> None:
    from src.skills.core.b1_city_dynamic import CityDynamicSkill
    from src.skills.core.d1_customer_survey import CustomerSurveySkill
    from src.skills.core.f1_extreme_event import ExtremeEventSkill
    from src.skills.core.g2_diversion import DiversionManagementSkill
    from src.skills.core.h1_cross_validation import CrossValidationSkill
    from src.skills.core.f6_fallback import FallbackSkill
    from src.skills.registry import SkillMetadata
    from src.skills.schema import SkillCategory

    category_map = {
        "B1_city_dynamic": SkillCategory.CORE_PREDICTION,
        "D1_customer_survey": SkillCategory.CORE_PREDICTION,
        "F1_extreme_event": SkillCategory.CORE_PREDICTION,
        "G2_diversion_management": SkillCategory.CORE_PREDICTION,
        "H1_cross_validation": SkillCategory.VALIDATION,
        "F6_historical_median": SkillCategory.CORE_PREDICTION,
    }

    skill_classes = [
        CityDynamicSkill, CustomerSurveySkill, ExtremeEventSkill,
        DiversionManagementSkill, CrossValidationSkill, FallbackSkill,
    ]

    for cls in skill_classes:
        skill = cls()
        metadata = SkillMetadata(
            skill_id=skill.skill_id,
            name=skill.name,
            category=category_map.get(skill.skill_id, SkillCategory.CORE_PREDICTION),
            version=skill.version,
            description=skill.name,
            required_evidence=[],
            optional_evidence=[],
            recommended_scenarios=[],
            not_recommended_for=[],
            avg_mape=skill.avg_mape,
            avg_latency_ms=skill.avg_latency_ms,
        )
        registry.register(skill, metadata)
