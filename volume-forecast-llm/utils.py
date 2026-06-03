"""工具函数"""

import logging
import json
from datetime import datetime
from typing import Any, Dict

# 日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("volume-forecast")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_json(obj: Any, indent: int = 2) -> str:
    """安全 JSON 序列化"""
    def _default(o):
        if hasattr(o, "strftime"):
            return o.strftime("%Y-%m-%d")
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)

    return json.dumps(obj, ensure_ascii=False, indent=indent, default=_default)


def safe_div(a, b, default=0.0):
    """安全除法"""
    return a / b if b != 0 else default


def groupby_date_range(events: list, date_key: str = "date") -> Dict[str, list]:
    """按日期分组事件"""
    result = {}
    for ev in events:
        d = ev.get(date_key, "")
        if d not in result:
            result[d] = []
        result[d].append(ev)
    return result
