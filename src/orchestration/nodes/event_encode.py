"""event_encode node — Convert unstructured events to structured vectors (LLM, ~800 tokens)."""

from __future__ import annotations

from src.orchestration.state import ForecastState


async def event_encode_node(state: ForecastState) -> dict:
    """Encode unstructured event text into structured feature vectors.

    🔴 LLM call: ~800 tokens (only when has_unstructured_event is True).
    This runs once per prediction — all Skills share the encoded result.

    In production, this calls an LLM to semantically parse event text.
    For MVP, we use a structured mapping from event types to feature vectors.
    """
    intent = state["intent"]
    events = intent.get("events", [])

    if not events:
        return {"token_used": state.get("token_used", 0)}

    event_vectors = []
    for evt in events:
        vector = _encode_event(evt)
        event_vectors.append(vector)

    existing_evidence = state.get("evidence", {})
    existing_entries = existing_evidence.get("entries", {})
    existing_entries["event_vector"] = existing_entries.get("event_vector", [])

    for vec in event_vectors:
        existing_entries["event_vector"].append({
            "type": "event_vector",
            "source": "event_encoder",
            "content_ref": f"encoded:{vec['event_type']}",
            "quality_score": 0.80,
            "metadata": vec,
        })

    existing_evidence["entries"] = existing_entries

    return {
        "evidence": existing_evidence,
        "token_used": state.get("token_used", 0) + 800,
    }


def _encode_event(event: dict) -> dict:
    event_type = event.get("type", "unknown")
    keyword = event.get("keyword", "")

    encodings = {
        "live_stream": {
            "event_type": "customer_promotion",
            "severity": 3,
            "estimated_volume_uplift": 1.20,
            "confidence": 0.75,
            "time_window": {"start": "00:00", "end": "23:59"},
        },
        "promotion": {
            "event_type": "platform_promotion",
            "severity": 4,
            "estimated_volume_uplift": 1.35,
            "confidence": 0.80,
            "time_window": {"start": "00:00", "end": "23:59"},
        },
        "typhoon": {
            "event_type": "weather_extreme",
            "severity": 4,
            "estimated_volume_decay": 0.70,
            "estimated_delay_hours": 4,
            "confidence": 0.70,
        },
        "rainstorm": {
            "event_type": "weather_extreme",
            "severity": 3,
            "estimated_volume_decay": 0.85,
            "estimated_delay_hours": 2,
            "confidence": 0.75,
        },
        "snowstorm": {
            "event_type": "weather_extreme",
            "severity": 4,
            "estimated_volume_decay": 0.60,
            "estimated_delay_hours": 6,
            "confidence": 0.72,
        },
        "fog": {
            "event_type": "weather_extreme",
            "severity": 2,
            "estimated_volume_decay": 0.92,
            "estimated_delay_hours": 1,
            "confidence": 0.80,
        },
        "diversion": {
            "event_type": "overflow_diversion",
            "severity": 3,
            "estimated_volume_uplift": 1.15,
            "confidence": 0.65,
        },
        "shift_close": {
            "event_type": "capacity_reduction",
            "severity": 3,
            "estimated_volume_uplift": 1.10,
            "confidence": 0.70,
        },
        "road_closure": {
            "event_type": "route_disruption",
            "severity": 3,
            "estimated_delay_hours": 3,
            "confidence": 0.65,
        },
        "new_customer": {
            "event_type": "customer_change",
            "severity": 2,
            "estimated_volume_uplift": 1.05,
            "confidence": 0.50,
        },
        "charter_flight": {
            "event_type": "customer_promotion",
            "severity": 3,
            "estimated_volume_uplift": 1.25,
            "confidence": 0.70,
        },
    }

    return encodings.get(event_type, {
        "event_type": "unknown",
        "severity": 1,
        "confidence": 0.30,
    })
