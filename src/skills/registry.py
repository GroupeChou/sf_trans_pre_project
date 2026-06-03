"""Skill Registry — Central registry for all prediction Skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.skills.base import BaseSkill
from src.skills.schema import SkillCategory


@dataclass
class SkillMetadata:
    skill_id: str
    name: str
    category: SkillCategory
    version: str
    description: str
    required_evidence: list[str]
    optional_evidence: list[str]
    recommended_scenarios: list[str]
    not_recommended_for: list[str]
    avg_mape: float
    avg_latency_ms: int
    priority: int = 50


class SkillRegistry:
    """Central registry for all prediction Skills in the marketplace."""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._metadata: dict[str, SkillMetadata] = {}
        self._status: dict[str, str] = {}

    def register(
        self,
        skill: BaseSkill,
        metadata: SkillMetadata | None = None,
        status: str = "published",
    ) -> None:
        sid = skill.skill_id
        self._skills[sid] = skill
        self._status[sid] = status

        if metadata:
            self._metadata[sid] = metadata
        else:
            self._metadata[sid] = SkillMetadata(
                skill_id=sid,
                name=skill.name,
                category=skill.category,
                version=skill.version,
                description="",
                required_evidence=[],
                optional_evidence=[],
                recommended_scenarios=[],
                not_recommended_for=[],
                avg_mape=skill.avg_mape,
                avg_latency_ms=skill.avg_latency_ms,
            )

    def get(self, skill_id: str) -> BaseSkill | None:
        return self._skills.get(skill_id)

    def get_metadata(self, skill_id: str) -> SkillMetadata | None:
        return self._metadata.get(skill_id)

    def get_status(self, skill_id: str) -> str:
        return self._status.get(skill_id, "unknown")

    def list_published(self, category: SkillCategory | None = None) -> list[str]:
        skills = []
        for sid, status in self._status.items():
            if status != "published":
                continue
            if category and self._metadata.get(sid) and self._metadata[sid].category != category:
                continue
            skills.append(sid)
        return skills

    def list_all(self) -> list[str]:
        return list(self._skills.keys())

    def list_by_category(self, category: SkillCategory) -> list[str]:
        return [
            sid for sid, meta in self._metadata.items()
            if meta.category == category and self._status.get(sid) == "published"
        ]

    def is_published(self, skill_id: str) -> bool:
        return self._status.get(skill_id) == "published"

    def deprecate(self, skill_id: str) -> None:
        self._status[skill_id] = "deprecated"

    def retire(self, skill_id: str) -> None:
        self._status[skill_id] = "retired"

    def get_all_metadata(self) -> dict[str, SkillMetadata]:
        return dict(self._metadata)

    def size(self) -> int:
        return len(self._skills)

    def clear(self) -> None:
        self._skills.clear()
        self._metadata.clear()
        self._status.clear()
