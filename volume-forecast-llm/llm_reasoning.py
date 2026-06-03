"""LLM 推理引擎 — 核心模块：推理促销调整因子"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .config import LLMConfig, PromotionConfig
from .utils import logger


class LLMReasoningEngine:
    """
    LLM 推理引擎

    不做数值预测，只推理调整因子。
    核心逻辑：历史增幅为锚 → LLM 推理今年 vs 去年的差异 → 输出修正后的每日调整因子
    """

    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()

    # ----------------------------------------------------------------
    # 构建推理上下文
    # ----------------------------------------------------------------
    def build_reasoning_context(
        self,
        promotion_events: List[Dict],
        calendar_comparison: Dict,
        historical_lifts_text: str,
        prophet_baseline: pd.DataFrame,
        additional_context: str = "",
        forecast_days: int = 60,
    ) -> dict:
        """
        组装 LLM 推理所需的完整结构化上下文

        注意：这个函数不调用 LLM，只做数据准备。
        LLM 调用由 pipeline 层完成，这样可以灵活切换 LLM 后端。
        """
        # Prophet 基线摘要
        future_baseline = prophet_baseline.tail(forecast_days)
        baseline_summary = {
            "start_date": future_baseline["ds"].min().strftime("%Y-%m-%d"),
            "end_date": future_baseline["ds"].max().strftime("%Y-%m-%d"),
            "avg_daily": round(float(future_baseline["yhat"].mean()), 0),
            "total": round(float(future_baseline["yhat"].sum()), 0),
            "trend": "up" if future_baseline["yhat"].iloc[-1] > future_baseline["yhat"].iloc[0] else "down",
        }

        # 促销事件摘要（用于 LLM 快速理解）
        promo_summary = []
        for ev in promotion_events:
            promo_summary.append({
                "platform": ev.get("platform", ""),
                "phase": ev.get("event_name", ""),
                "date": ev.get("start_date", ""),
                "confidence": ev.get("confidence", "unconfirmed"),
            })

        return {
            "forecast_days": forecast_days,
            "baseline_summary": baseline_summary,
            "promotion_events": promo_summary,
            "calendar_comparison": calendar_comparison,
            "historical_lifts": historical_lifts_text,
            "additional_context": additional_context or "无额外上下文",
        }

    def build_prompt(self, context: dict) -> str:
        """根据上下文构建完整 LLM prompt"""
        return self.config.reasoning_prompt.format(
            forecast_days=context["forecast_days"],
            calendar_comparison=json.dumps(context["calendar_comparison"], ensure_ascii=False, indent=2),
            historical_lifts=context["historical_lifts"],
            additional_context=context["additional_context"],
            min_factor=self.config.min_factor,
            max_factor=self.config.max_factor,
            max_deviation_pct=f"{int(self.config.max_deviation_from_last_year * 100)}",
            promotion_name=", ".join(
                set(e.get("platform", "") for e in context.get("promotion_events", []))
            ),
        )

    # ----------------------------------------------------------------
    # 输出解析与校验
    # ----------------------------------------------------------------
    def parse_llm_output(self, llm_response: str) -> Dict:
        """解析 LLM 输出的 JSON，做安全校验"""
        # 清理 markdown 包裹
        response = llm_response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            response = response.rsplit("```", 1)[0]
        if "{" not in response:
            logger.error("LLM 输出不是有效 JSON")
            return {"error": "invalid_json", "raw": llm_response[:500]}

        response = response[response.index("{"):]

        try:
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return {"error": "json_parse_error", "raw": response[:500]}

        return result

    def validate_adjustments(self, adjustments: List[Dict]) -> List[Dict]:
        """校验调整因子的合理性"""
        validated = []
        for adj in adjustments:
            factors = adj.get("daily_factors", {})
            clean_factors = {}

            for date_str, factor in factors.items():
                factor = float(factor)
                # 范围约束
                factor = max(self.config.min_factor, min(self.config.max_factor, factor))
                # 不允许 NaN/Inf
                if np.isnan(factor) or np.isinf(factor):
                    factor = 1.0
                clean_factors[date_str] = round(factor, 3)

            adj["daily_factors"] = clean_factors
            validated.append(adj)

        return validated

    # ----------------------------------------------------------------
    # 一站式：构建 prompt + 解析输出（由 pipeline 串联 LLM 调用）
    # ----------------------------------------------------------------
    def prepare_for_llm(
        self,
        promotion_events: List[Dict],
        calendar_comparison: Dict,
        historical_lifts_text: str,
        prophet_baseline: pd.DataFrame,
        additional_context: str = "",
        forecast_days: int = 60,
    ) -> Dict:
        """
        一站式准备：构建 context → 构建 prompt → 返回
        实际 LLM 调用由外层 pipeline 执行
        """
        context = self.build_reasoning_context(
            promotion_events=promotion_events,
            calendar_comparison=calendar_comparison,
            historical_lifts_text=historical_lifts_text,
            prophet_baseline=prophet_baseline,
            additional_context=additional_context,
            forecast_days=forecast_days,
        )
        prompt = self.build_prompt(context)

        return {
            "context": context,
            "prompt": prompt,
            "parse_fn": self.parse_llm_output,      # 回调给 pipeline
            "validate_fn": self.validate_adjustments,  # 回调给 pipeline
        }
