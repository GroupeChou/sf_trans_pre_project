"""Evidence Blackboard — Unified source of truth for all prediction evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    TIMESERIES_VOLUME = "timeseries_volume"
    BUSINESS_ZONE_FORECAST = "business_zone_forecast"
    CITY_DYNAMIC_FORECAST = "city_dynamic_forecast"
    VEHICLE_ETA_LIST = "vehicle_eta_list"
    CUSTOMER_REPORTED_VOLUME = "customer_reported_volume"
    WEATHER_ALERT = "weather_alert"
    DIVERSION_RECORD = "diversion_record"
    HUMAN_NOTE = "human_note"
    EVENT_VECTOR = "event_vector"


class EvidenceEntry(BaseModel):
    type: EvidenceType
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_ref: str
    ttl_seconds: int = 300
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def cache_key(self) -> str:
        content = f"{self.type.value}:{self.source}:{self.content_ref}"
        return hashlib.md5(content.encode()).hexdigest()


class EvidenceBlackboard:
    """Unified evidence board. All Skills read data through this single entry point."""

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self._entries: dict[EvidenceType, list[EvidenceEntry]] = {}
        self._quality_summary: dict[str, Any] = {}

    def add(self, entry: EvidenceEntry) -> None:
        if entry.type not in self._entries:
            self._entries[entry.type] = []
        self._entries[entry.type].append(entry)

    def get(self, evidence_type: EvidenceType) -> list[EvidenceEntry]:
        return self._entries.get(evidence_type, [])

    def get_all(self) -> dict[EvidenceType, list[EvidenceEntry]]:
        return dict(self._entries)

    def has_type(self, evidence_type: EvidenceType) -> bool:
        return evidence_type in self._entries and len(self._entries[evidence_type]) > 0

    def calculate_completeness(self, required_types: list[EvidenceType]) -> float:
        if not required_types:
            return 1.0
        available = sum(1 for t in required_types if self.has_type(t))
        return available / len(required_types)

    def summarize(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "evidence_types": list(self._entries.keys()),
            "entry_count": sum(len(v) for v in self._entries.values()),
            "completeness": self._quality_summary.get("completeness", 0.0),
            "average_quality": self._quality_summary.get("average_quality", 0.0),
            "has_unstructured_event": self.has_type(EvidenceType.EVENT_VECTOR),
        }

    def set_quality_summary(self, completeness: float, avg_quality: float) -> None:
        self._quality_summary = {
            "completeness": completeness,
            "average_quality": avg_quality,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "entries": {
                k.value: [e.model_dump(mode="json") for e in v]
                for k, v in self._entries.items()
            },
            "quality_summary": self._quality_summary,
        }
