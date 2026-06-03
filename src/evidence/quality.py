"""Data quality scoring for the Evidence Blackboard."""

from __future__ import annotations

from src.evidence.blackboard import EvidenceBlackboard, EvidenceType


def score_data_quality(blackboard: EvidenceBlackboard) -> dict:
    """Score the data quality across all evidence types."""
    entries = blackboard.get_all()

    if not entries:
        return {
            "completeness": 0.0,
            "average_quality": 0.0,
            "level": "critical",
            "message": "No evidence available",
        }

    quality_scores = []
    for entries_list in entries.values():
        for entry in entries_list:
            quality_scores.append(entry.quality_score)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    completeness = _calculate_completeness(entries)

    level = _determine_level(completeness, avg_quality)

    return {
        "completeness": round(completeness, 2),
        "average_quality": round(avg_quality, 2),
        "level": level,
    }


def _calculate_completeness(entries: dict) -> float:
    critical_types = {
        EvidenceType.TIMESERIES_VOLUME,
    }
    important_types = {
        EvidenceType.CITY_DYNAMIC_FORECAST,
        EvidenceType.BUSINESS_ZONE_FORECAST,
    }

    critical_available = sum(1 for t in critical_types if t in entries)
    important_available = sum(1 for t in important_types if t in entries)

    if critical_available == 0:
        return 0.0
    return 0.6 * (critical_available / len(critical_types)) + 0.4 * (
        important_available / len(important_types)
    )


def _determine_level(completeness: float, avg_quality: float) -> str:
    if completeness >= 0.85 and avg_quality >= 0.80:
        return "high"
    elif completeness >= 0.50 and avg_quality >= 0.50:
        return "medium"
    elif completeness >= 0.30:
        return "low"
    else:
        return "critical"
