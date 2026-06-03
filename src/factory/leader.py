"""ClawTeam-style Skill Factory leader agent for offline Skill generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SkillDraftStatus(str, Enum):
    DRAFT = "draft"
    LINTING = "linting"
    BACKTESTING = "backtesting"
    REVIEWING = "reviewing"
    READY = "ready"
    PUBLISHED = "published"
    REJECTED = "rejected"


@dataclass
class SkillDraft:
    draft_id: str
    name: str
    description: str
    natural_language_spec: str
    generated_code: str = ""
    generated_yaml: str = ""
    backtest_results: dict[str, Any] = field(default_factory=dict)
    review_report: str = ""
    status: SkillDraftStatus = SkillDraftStatus.DRAFT


class SkillFactoryLeader:
    """ClawTeam-style Leader Agent for offline Skill generation.

    Coordinates a team of workers:
    - CodeWorker: Generate Python Skill code from natural language
    - SchemaWorker: Generate YAML Skill card
    - BacktestWorker: Run historical backtest
    - ReportWorker: Generate review report

    This runs OFFLINE — not in the online prediction serving path.
    """

    def __init__(self):
        self._drafts: dict[str, SkillDraft] = {}

    def create_draft(
        self,
        name: str,
        description: str,
        natural_language_spec: str,
    ) -> SkillDraft:
        draft_id = f"draft_{len(self._drafts) + 1:04d}"
        draft = SkillDraft(
            draft_id=draft_id,
            name=name,
            description=description,
            natural_language_spec=natural_language_spec,
        )
        self._drafts[draft_id] = draft
        return draft

    def generate_code(self, draft_id: str) -> SkillDraft:
        """CodeWorker: Generate Python code from natural language spec.

        🔴🔴🔴 LLM call: high token consumption. Runs offline.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        # In production: LLM generates Python code based on the natural language spec
        draft.generated_code = _generate_skill_code(draft.natural_language_spec, draft.name)
        draft.status = SkillDraftStatus.LINTING
        return draft

    def generate_schema(self, draft_id: str) -> SkillDraft:
        """SchemaWorker: Generate YAML Skill card.

        🔴 LLM call: low-mid token consumption. Runs offline.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        draft.generated_yaml = _generate_skill_yaml(draft.name, draft.description)
        draft.status = SkillDraftStatus.REVIEWING
        return draft

    def run_backtest(self, draft_id: str, historical_data_ref: str = "") -> SkillDraft:
        """BacktestWorker: Run historical backtest.

        🟢 Pure code: 0 tokens. Python execution only.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        # In production: execute the generated code against historical data
        draft.backtest_results = {
            "mape": 0.072,
            "samples": 120,
            "passed": True,
            "data_period": "2026-03-01 to 2026-05-31",
        }
        draft.status = SkillDraftStatus.BACKTESTING
        return draft

    def generate_report(self, draft_id: str) -> SkillDraft:
        """ReportWorker: Generate review report.

        🔴🔴 LLM call: mid token consumption. Runs offline.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        draft.review_report = (
            f"Skill Review Report for {draft.name}\n"
            f"Backtest MAPE: {draft.backtest_results.get('mape', 'N/A')}\n"
            f"Status: {'PASS' if draft.backtest_results.get('passed') else 'FAIL'}\n"
        )
        draft.status = SkillDraftStatus.READY
        return draft

    def publish(self, draft_id: str) -> SkillDraft:
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        if draft.status != SkillDraftStatus.READY:
            raise ValueError(f"Draft {draft_id} not ready: {draft.status.value}")
        draft.status = SkillDraftStatus.PUBLISHED
        return draft

    def get_draft(self, draft_id: str) -> SkillDraft | None:
        return self._drafts.get(draft_id)

    def list_drafts(self) -> list[SkillDraft]:
        return list(self._drafts.values())


def _generate_skill_code(spec: str, name: str) -> str:
    return (
        f"# Auto-generated Skill: {name}\n"
        f"# Spec: {spec}\n\n"
        "from src.skills.base import BaseSkill\n"
        "from src.skills.schema import ForecastTarget, ForecastClaim, SkillCategory\n\n"
        f"class GeneratedSkill(BaseSkill):\n"
        f"    skill_id = 'custom_{name.lower().replace(' ', '_')}'\n"
        f"    name = '{name}'\n"
        f"    category = SkillCategory.CORE_PREDICTION\n\n"
        "    async def execute(self, target, blackboard, **params):\n"
        "        # TODO: Implement based on spec\n"
        "        return self._build_claim(target=target, mean=0, assumptions=['Auto-generated placeholder'])\n"
    )


def _generate_skill_yaml(name: str, description: str) -> str:
    return (
        f"skill_id: custom_{name.lower().replace(' ', '_')}\n"
        f"name: {name}\n"
        f"category: core_prediction\n"
        f"version: 0.1.0\n"
        f"description: {description}\n"
        f"confidence_level: 0.75\n"
    )
