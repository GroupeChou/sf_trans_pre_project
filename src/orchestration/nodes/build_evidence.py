"""build_evidence node — Populate Evidence Blackboard (pure code, 0 tokens)."""

from __future__ import annotations

from src.evidence.blackboard import EvidenceBlackboard, EvidenceEntry, EvidenceType
from src.evidence.quality import score_data_quality
from src.orchestration.state import ForecastState


async def build_evidence_node(state: ForecastState) -> dict:
    """Build the Evidence Blackboard with all available data sources.

    🟢 Pure code: 0 tokens. Queries data sources and populates the blackboard.
    """
    trace_id = state["trace_id"]
    intent = state["intent"]
    site_code = intent.get("site_code", "")
    target_date = intent.get("target_date", "")

    blackboard = EvidenceBlackboard(trace_id)

    _add_timeseries(blackboard, site_code, target_date)
    _add_city_dynamic(blackboard, site_code, target_date)

    events = intent.get("events", [])
    has_unstructured = False
    for evt in events:
        if evt["type"] in ("promotion", "live_stream", "charter_flight", "new_customer",
                           "typhoon", "rainstorm", "snowstorm", "fog"):
            blackboard.add(EvidenceEntry(
                type=EvidenceType.EVENT_VECTOR,
                source="user_input",
                content_ref=f"event:{evt['type']}:{evt.get('keyword','')}",
                quality_score=0.70,
            ))
            has_unstructured = True

    if any(evt["type"] == "diversion" for evt in events):
        _add_diversion(blackboard, site_code)

    if any(evt["type"] == "new_customer" for evt in events):
        _add_customer_report(blackboard, site_code)

    if any(evt["type"] in ("typhoon", "rainstorm", "snowstorm", "fog") for evt in events):
        _add_weather(blackboard, site_code)

    quality = score_data_quality(blackboard)
    blackboard.set_quality_summary(quality["completeness"], quality["average_quality"])

    evidence = blackboard.to_dict()
    evidence_summary = blackboard.summarize()

    return {
        "evidence": evidence,
        "evidence_summary": evidence_summary,
        "has_unstructured_event": has_unstructured,
    }


def _add_timeseries(bb: EvidenceBlackboard, site: str, date: str) -> None:
    bb.add(EvidenceEntry(
        type=EvidenceType.TIMESERIES_VOLUME,
        source="satis_oe_system",
        content_ref=f"timeseries:{site}:{date}:30d",
        quality_score=0.95,
    ))


def _add_city_dynamic(bb: EvidenceBlackboard, site: str, date: str) -> None:
    bb.add(EvidenceEntry(
        type=EvidenceType.CITY_DYNAMIC_FORECAST,
        source="satis_oewm_system",
        content_ref=f"city_dynamic:{site}:{date}",
        quality_score=0.90,
    ))


def _add_diversion(bb: EvidenceBlackboard, site: str) -> None:
    bb.add(EvidenceEntry(
        type=EvidenceType.DIVERSION_RECORD,
        source="satis_oe_diversion",
        content_ref=f"diversion:{site}",
        quality_score=0.70,
    ))


def _add_customer_report(bb: EvidenceBlackboard, site: str) -> None:
    bb.add(EvidenceEntry(
        type=EvidenceType.CUSTOMER_REPORTED_VOLUME,
        source="kadm_system",
        content_ref=f"customer_report:{site}",
        quality_score=0.75,
    ))


def _add_weather(bb: EvidenceBlackboard, site: str) -> None:
    bb.add(EvidenceEntry(
        type=EvidenceType.WEATHER_ALERT,
        source="weather_api",
        content_ref=f"weather:{site}",
        quality_score=0.85,
    ))
