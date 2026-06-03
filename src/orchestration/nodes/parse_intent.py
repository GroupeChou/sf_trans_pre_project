"""parse_intent node — Extract intent from natural language (LLM, ~300 tokens)."""

from __future__ import annotations

from src.orchestration.state import ForecastState


async def parse_intent_node(state: ForecastState) -> dict:
    """Parse user's natural language request into structured intent.

    🔴 LLM call: ~300 tokens. In production, uses Claude/other LLM.
    For MVP, uses rule-based extraction with key phrase matching.
    """
    text = state["request"].get("text", "")
    site = state["request"].get("site", "")
    target_date = state["request"].get("date", "")

    events = _extract_events(text)
    dimensions = _extract_dimensions(text)
    prediction_type = _classify_prediction_type(text, events)

    intent = {
        "site_code": site,
        "target_date": target_date,
        "events": events,
        "dimensions": dimensions,
        "prediction_type": prediction_type,
        "original_text": text,
    }

    return {
        "intent": intent,
        "token_used": state.get("token_used", 0) + 300,
    }


def _extract_events(text: str) -> list[dict]:
    events = []
    event_keywords = {
        "直播": "live_stream",
        "促销": "promotion",
        "618": "promotion",
        "双11": "promotion",
        "台风": "typhoon",
        "暴雨": "rainstorm",
        "暴雪": "snowstorm",
        "大雾": "fog",
        "倒货": "diversion",
        "关班": "shift_close",
        "封路": "road_closure",
        "新客户": "new_customer",
        "包机": "charter_flight",
    }
    for kw, event_type in event_keywords.items():
        if kw in text:
            events.append({"type": event_type, "keyword": kw})
    return events


def _extract_dimensions(text: str) -> list[str]:
    dims = []
    dim_keywords = {
        "白班": "shift_day",
        "夜班": "shift_night",
        "晚班": "shift_night",
        "库区": "warehouse",
        "集货": "collection",
        "散货": "distribution",
        "经济圈": "economic_zone",
        "客户": "customer",
    }
    for kw, dim in dim_keywords.items():
        if kw in text:
            dims.append(dim)
    return dims if dims else ["site_total"]


def _classify_prediction_type(text: str, events: list) -> str:
    if events:
        for evt in events:
            if evt["type"] in ("typhoon", "rainstorm", "snowstorm", "fog"):
                return "weather_impact"
            if evt["type"] in ("promotion", "live_stream"):
                return "promotion_impact"
        return "event_impact"
    if any(kw in text for kw in ["班次", "白班", "夜班", "晚班"]):
        return "shift_prediction"
    if any(kw in text for kw in ["库区"]):
        return "warehouse_prediction"
    return "daily_routine"
