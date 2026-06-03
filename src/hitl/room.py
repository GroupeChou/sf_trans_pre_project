"""HiClaw-style HITL collaboration room for high-risk predictions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HITLStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    ADJUSTED = "adjusted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class HITLAction(str, Enum):
    CONFIRM = "confirm"
    ADJUST_UP = "adjust_up"
    ADJUST_DOWN = "adjust_down"
    RERUN = "rerun"
    VIEW_EVIDENCE = "view_evidence"
    ROLLBACK = "rollback"


@dataclass
class HITLSession:
    session_id: str
    trace_id: str
    site_code: str
    status: HITLStatus = HITLStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Claims from Agent Team
    agent_claims: list[dict] = field(default_factory=list)
    disagreement_index: float = 0.0
    difficulty_level: str = "medium"

    # Human input
    human_decision: HITLAction | None = None
    adjusted_value: float | None = None
    adjust_reason: str = ""
    reviewer: str = ""

    # Timeline
    assigned_at: str | None = None
    decided_at: str | None = None
    expires_at: str | None = None

    def to_display_card(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "site_code": self.site_code,
            "status": self.status.value,
            "disagreement_index": self.disagreement_index,
            "agent_claims": [
                {
                    "skill": c.get("skill_id", "unknown"),
                    "mean": c.get("claim", {}).get("mean"),
                    "confidence": c.get("claim", {}).get("confidence"),
                }
                for c in self.agent_claims
            ],
            "actions_available": [a.value for a in HITLAction],
            "created_at": self.created_at,
        }


class CollaborationRoom:
    """HiClaw-style collaboration room for high-risk prediction review.

    Triggers when:
    - DI >= 0.50
    - High-impact events with missing evidence
    - All formal Skills failed, only F6 remains
    """

    def __init__(self):
        self._sessions: dict[str, HITLSession] = {}

    def create_session(
        self,
        trace_id: str,
        site_code: str,
        agent_claims: list[dict],
        disagreement_index: float,
        difficulty_level: str,
    ) -> HITLSession:
        session_id = f"hitl_{trace_id}"
        session = HITLSession(
            session_id=session_id,
            trace_id=trace_id,
            site_code=site_code,
            agent_claims=agent_claims,
            disagreement_index=disagreement_index,
            difficulty_level=difficulty_level,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> HITLSession | None:
        return self._sessions.get(session_id)

    def decide(
        self,
        session_id: str,
        action: HITLAction,
        reviewer: str,
        adjusted_value: float | None = None,
        reason: str = "",
    ) -> HITLSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.human_decision = action
        session.reviewer = reviewer
        session.adjust_reason = reason
        session.decided_at = datetime.utcnow().isoformat()

        if action == HITLAction.CONFIRM:
            session.status = HITLStatus.APPROVED
        elif action in (HITLAction.ADJUST_UP, HITLAction.ADJUST_DOWN):
            session.status = HITLStatus.ADJUSTED
            session.adjusted_value = adjusted_value
        elif action == HITLAction.ROLLBACK:
            session.status = HITLStatus.REJECTED

        return session

    def active_sessions(self) -> list[HITLSession]:
        return [
            s for s in self._sessions.values()
            if s.status in (HITLStatus.PENDING, HITLStatus.REVIEWING)
        ]
