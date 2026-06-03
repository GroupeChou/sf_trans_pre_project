"""run_skills node — Parallel execution of selected Skills (pure code, 0 tokens)."""

from __future__ import annotations

import asyncio

from src.evidence.blackboard import EvidenceBlackboard
from src.orchestration.state import ForecastState
from src.skills.base import BaseSkill
from src.skills.schema import ForecastTarget, TargetDimension


async def run_skills_node(state: ForecastState) -> dict:
    """Run all selected Skills in parallel and collect their ForecastClaims.

    🟢 Pure code: 0 tokens (10/12 Skills are deterministic Python code).
    Uses asyncio.gather for parallel execution.
    """
    selected = state.get("selected_skills", [])
    intent = state.get("intent", {})
    trace_id = state["trace_id"]

    target = ForecastTarget(
        site_code=intent.get("site_code", "UNKNOWN"),
        target_date=intent.get("target_date", ""),
        dimension=_map_dimension(intent.get("dimensions", ["site_total"])[0]),
    )

    blackboard = EvidenceBlackboard(trace_id)

    from src.skills.registry import SkillRegistry
    registry = SkillRegistry()
    _register_all_skills(registry)

    tasks = []
    for skill_id in selected:
        skill = registry.get(skill_id)
        if skill is not None:
            tasks.append(skill.run(target, blackboard))

    claims = await asyncio.gather(*tasks, return_exceptions=True)

    skill_claims = []
    for claim in claims:
        if isinstance(claim, Exception):
            skill_claims.append({
                "error": str(claim),
                "trace_id": trace_id,
            })
        else:
            skill_claims.append(claim.model_dump())

    return {"skill_claims": skill_claims}


def _register_all_skills(registry) -> None:
    from src.skills.core.b1_city_dynamic import CityDynamicSkill
    from src.skills.core.d1_customer_survey import CustomerSurveySkill
    from src.skills.core.f1_extreme_event import ExtremeEventSkill
    from src.skills.core.g2_diversion import DiversionManagementSkill
    from src.skills.core.h1_cross_validation import CrossValidationSkill
    from src.skills.core.f6_fallback import FallbackSkill
    from src.skills.registry import SkillMetadata
    from src.skills.schema import SkillCategory

    skill_classes = [
        CityDynamicSkill,
        CustomerSurveySkill,
        ExtremeEventSkill,
        DiversionManagementSkill,
        CrossValidationSkill,
        FallbackSkill,
    ]

    for cls in skill_classes:
        skill = cls()
        category_map = {
            "B1_city_dynamic": SkillCategory.CORE_PREDICTION,
            "D1_customer_survey": SkillCategory.CORE_PREDICTION,
            "F1_extreme_event": SkillCategory.CORE_PREDICTION,
            "G2_diversion_management": SkillCategory.CORE_PREDICTION,
            "H1_cross_validation": SkillCategory.VALIDATION,
            "F6_historical_median": SkillCategory.CORE_PREDICTION,
        }
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


def _map_dimension(dim_str: str) -> TargetDimension:
    mapping = {
        "site_total": TargetDimension.SITE_TOTAL,
        "shift_day": TargetDimension.SHIFT_LEVEL,
        "shift_night": TargetDimension.SHIFT_LEVEL,
        "warehouse": TargetDimension.WAREHOUSE_LEVEL,
        "collection": TargetDimension.COLLECTION_DISTRIBUTION,
        "distribution": TargetDimension.COLLECTION_DISTRIBUTION,
        "economic_zone": TargetDimension.ECONOMIC_ZONE,
        "customer": TargetDimension.CUSTOMER,
    }
    return mapping.get(dim_str, TargetDimension.SITE_TOTAL)
