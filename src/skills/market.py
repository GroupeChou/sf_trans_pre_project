"""Skills Market — Management UI backend for the Skills marketplace."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.skills.registry import SkillRegistry, SkillMetadata
from src.skills.schema import SkillCategory


@dataclass
class SceneTemplate:
    template_id: str
    name: str
    description: str
    skill_ids: list[str]
    default_params: dict[str, dict] = field(default_factory=dict)
    trigger_words: list[str] = field(default_factory=list)


class SkillsMarket:
    """Backend for the Skills Market management UI."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._templates: dict[str, SceneTemplate] = {}

    def register_template(self, template: SceneTemplate) -> None:
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> SceneTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[SceneTemplate]:
        return list(self._templates.values())

    def find_template_by_trigger(self, text: str) -> SceneTemplate | None:
        for tpl in self._templates.values():
            for word in tpl.trigger_words:
                if word in text:
                    return tpl
        return None

    def search_skills(self, query: str | None = None, category: SkillCategory | None = None) -> list[SkillMetadata]:
        results = []
        for sid in self.registry.list_published(category):
            meta = self.registry.get_metadata(sid)
            if meta is None:
                continue
            if query and query.lower() not in meta.name.lower() and query.lower() not in meta.description.lower():
                continue
            results.append(meta)
        return results

    def get_skill_stats(self, skill_id: str) -> dict:
        meta = self.registry.get_metadata(skill_id)
        if not meta:
            return {}
        return {
            "skill_id": meta.skill_id,
            "name": meta.name,
            "status": self.registry.get_status(skill_id),
            "avg_mape": meta.avg_mape,
            "avg_latency_ms": meta.avg_latency_ms,
            "priority": meta.priority,
            "category": meta.category.value,
        }
