"""Full-chain prediction tracer — Records every step of every prediction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TraceEvent:
    trace_id: str
    step: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    input_state: dict[str, Any] = field(default_factory=dict)
    output_state: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    token_used: int = 0
    error: str | None = None


class PredictionTracer:
    """Records complete execution trace for every prediction request.

    In production: sends data to Langfuse or similar observability platform.
    """

    def __init__(self):
        self._traces: dict[str, list[TraceEvent]] = {}

    def record(self, event: TraceEvent) -> None:
        if event.trace_id not in self._traces:
            self._traces[event.trace_id] = []
        self._traces[event.trace_id].append(event)

    def get_trace(self, trace_id: str) -> list[TraceEvent]:
        return self._traces.get(trace_id, [])

    def get_timeline(self, trace_id: str) -> list[dict[str, Any]]:
        events = self.get_trace(trace_id)
        return [
            {
                "step": e.step,
                "timestamp": e.timestamp,
                "duration_ms": e.duration_ms,
                "token_used": e.token_used,
                "error": e.error,
            }
            for e in events
        ]

    def get_token_summary(self, trace_id: str) -> dict[str, int]:
        events = self.get_trace(trace_id)
        total = sum(e.token_used for e in events)
        llm_steps = sum(1 for e in events if e.token_used > 0)
        return {
            "total_tokens": total,
            "llm_steps": llm_steps,
            "code_steps": len(events) - llm_steps,
        }

    def clear(self) -> None:
        self._traces.clear()
