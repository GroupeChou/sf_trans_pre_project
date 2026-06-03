"""历史促销增幅计算模块"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .utils import logger, safe_div


class PromotionLiftAnalyzer:
    """计算历史促销事件的实际增幅因子，构建促销增幅知识库"""

    def __init__(self):
        self.lift_db: Dict[str, Dict] = {}  # 促销增幅知识库

    def compute_historical_lifts(
        self,
        df_actual: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        promotion_events: List[Dict],
    ) -> Dict[str, Dict]:
        """
        对每个历史促销事件，计算：
          daily_lift = 实际件量 / Prophet预测值
          avg_lift   = 促销期平均增幅
          peak_lift  = 峰值增幅
          peak_day_offset = 峰值出现在第几天
        """
        logger.info(f"计算历史促销增幅: {len(promotion_events)} 个事件")

        for event in promotion_events:
            event_name = f"{event.get('platform', '')}_{event.get('event_name', '')}_{event.get('start_date', '')}"

            try:
                start = pd.Timestamp(event["start_date"])
                end = pd.Timestamp(event.get("end_date", event["start_date"]))
            except (KeyError, ValueError):
                logger.warning(f"跳过无效事件: {event}")
                continue

            # 该时间窗的实际值和预测值
            actual_window = df_actual[
                (df_actual["ds"] >= start) & (df_actual["ds"] <= end)
            ]
            forecast_window = prophet_forecast[
                (prophet_forecast["ds"] >= start) & (prophet_forecast["ds"] <= end)
            ]

            if actual_window.empty or forecast_window.empty:
                continue

            # 对齐日期
            merged = actual_window.merge(forecast_window, on="ds", suffixes=("_actual", "_fc"))
            merged["daily_lift"] = safe_div(merged["y"], merged["yhat"])

            if len(merged) == 0:
                continue

            daily_lifts = merged["daily_lift"].values
            peak_idx = np.argmax(daily_lifts)

            self.lift_db[event_name] = {
                "event_name": event_name,
                "platform": event.get("platform", ""),
                "event_type": event.get("event_name", ""),
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "duration_days": len(merged),
                "avg_lift": round(float(np.mean(daily_lifts)), 3),
                "peak_lift": round(float(np.max(daily_lifts)), 3),
                "peak_day_offset": int(peak_idx),
                "peak_date": merged.iloc[peak_idx]["ds"].strftime("%Y-%m-%d"),
                "decay_pattern": [round(float(x), 3) for x in daily_lifts],
                "volume_actual_total": round(float(merged["y"].sum()), 0),
                "volume_prophet_total": round(float(merged["yhat"].sum()), 0),
            }

        logger.info(f"历史增幅计算完成: {len(self.lift_db)} 条记录")
        return self.lift_db

    def get_promotion_lift_summary(self, platform: str = None) -> Dict:
        """
        获取促销增幅摘要，按平台+事件类型聚合。

        返回示例:
        {
            "天猫618": {
                "预售开始": {"avg_lift": 1.08, "count": 2, "trend": "up"},
                "付尾款开始": {"avg_lift": 1.85, "count": 2, "trend": "up"},
            }
        }
        """
        summary = {}
        for key, rec in self.lift_db.items():
            plat = rec.get("platform", "")
            etype = rec.get("event_type", "")
            if platform and plat != platform:
                continue

            if plat not in summary:
                summary[plat] = {}
            if etype not in summary[plat]:
                summary[plat][etype] = {"lifts": [], "count": 0}

            summary[plat][etype]["lifts"].append(rec["avg_lift"])
            summary[plat][etype]["count"] += 1

        # 计算聚合值
        for plat, types in summary.items():
            for etype, info in types.items():
                lifts = info["lifts"]
                info["avg_lift"] = round(np.mean(lifts), 3)
                info["min_lift"] = round(np.min(lifts), 3)
                info["max_lift"] = round(np.max(lifts), 3)
                info["trend"] = "up" if len(lifts) >= 2 and lifts[-1] > lifts[0] else "down"
                del info["lifts"]

        return summary

    def format_for_llm_context(self) -> str:
        """
        将增幅知识库格式化为 LLM prompt 可读文本
        """
        summary = self.get_promotion_lift_summary()
        lines = []
        for plat, types in summary.items():
            lines.append(f"\n  【{plat}】")
            for etype, info in types.items():
                lines.append(
                    f"    {etype}: 平均增幅 {info['avg_lift']:.2f}x, "
                    f"范围 [{info['min_lift']:.2f}x ~ {info['max_lift']:.2f}x], "
                    f"趋势 {'↑上升' if info['trend'] == 'up' else '↓下降'} "
                    f"(基于 {info['count']} 次历史事件)"
                )
        return "\n".join(lines)
