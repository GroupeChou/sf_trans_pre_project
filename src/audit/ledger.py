"""Event sourcing ledger — Immutable audit log for all prediction actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LedgerEventType(str, Enum):
    PREDICTION_REQUESTED = "prediction_requested"
    INTENT_PARSED = "intent_parsed"
    EVIDENCE_BUILT = "evidence_built"
    SKILL_EXECUTED = "skill_executed"
    DEBATE_RAN = "debate_ran"
    FUSED = "fused"
    CALIBRATED = "calibrated"
    PUBLISHED = "published"
    HUMAN_ADJUSTED = "human_adjusted"
    HUMAN_CONFIRMED = "human_confirmed"
    SYSTEM_ERROR = "system_error"
    DEGRADED = "degraded"


@dataclass
class LedgerEntry:
    entry_id: str
    trace_id: str
    event_type: LedgerEventType
    actor: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class EventLedger:
    """Immutable event sourcing ledger for complete audit trail.

    Key principle: NEVER overwrite history. All actions are appended as events.
    """

    def __init__(self, retention_days: int = 365):
        self._entries: dict[str, list[LedgerEntry]] = {}
        self.retention_days = retention_days

    def append(self, entry: LedgerEntry) -> None:
        if entry.trace_id not in self._entries:
            self._entries[entry.trace_id] = []
        self._entries[entry.trace_id].append(entry)

    def get_timeline(self, trace_id: str) -> list[LedgerEntry]:
        return self._entries.get(trace_id, [])

    def reconstruct_final_state(self, trace_id: str) -> dict[str, Any]:
        """Reconstruct the final state by replaying all events."""
        entries = self.get_timeline(trace_id)
        state: dict[str, Any] = {}
        for entry in entries:
            if entry.after:
                state.update(entry.after)
        return state

    def query(
        self,
        event_type: LedgerEventType | None = None,
        actor: str | None = None,
        since: str | None = None,
    ) -> list[LedgerEntry]:
        results = []
        for entries in self._entries.values():
            for entry in entries:
                if event_type and entry.event_type != event_type:
                    continue
                if actor and entry.actor != actor:
                    continue
                if since and entry.timestamp < since:
                    continue
                results.append(entry)
        return results

    def clear(self) -> None:
        self._entries.clear()
