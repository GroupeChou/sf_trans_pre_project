"""农商特产季节性效应模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from .config import AgricultureConfig
from .utils import logger, safe_div


class AgricultureAnalyzer:
    """农商特产季节性效应分析"""

    def __init__(self, config: AgricultureConfig = None):
        self.config = config or AgricultureConfig()

    def identify_agri_series(
        self, l2_series: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """从 L2 板块×地区序列中识别农商品类序列"""
        agri_series = {}
        for name, df in l2_series.items():
            for seg in self.config.agri_segments:
                if seg in name:
                    agri_series[name] = df
                    logger.info(f"识别农商品类序列: {name}")
                    break
        return agri_series

    def is_in_season(self, date: datetime, product: str = None) -> bool:
        """判断当前日期是否在农商品类旺季"""
        date_str = date.strftime("%m-%d")
        for prod, (start, end) in self.config.seasonal_periods.items():
            if product and product not in prod:
                continue
            if start <= date_str <= end or (
                start > end and (date_str >= start or date_str <= end)
            ):
                return True
        return False

    def compute_seasonal_lift(
        self,
        df_actual: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        series_name: str,
    ) -> Dict:
        """
        计算农商品类的季节性增幅

        逻辑：去年同期的实际/Prophet比值 → 今年的农商效应
        跟促销效应不同，农商效应更稳定，以数据驱动为主
        """
        logger.info(f"计算农商季节性增幅: {series_name}")

        # 去年同期的数据
        today = datetime.now()
        last_year_start = today.replace(year=today.year - 1) - pd.Timedelta(days=30)
        last_year_end = today.replace(year=today.year - 1) + pd.Timedelta(days=90)

        last_year_actual = df_actual[
            (df_actual["ds"] >= last_year_start) & (df_actual["ds"] <= last_year_end)
        ]
        last_year_fc = prophet_forecast[
            (prophet_forecast["ds"] >= last_year_start) & (prophet_forecast["ds"] <= last_year_end)
        ]

        if last_year_actual.empty or last_year_fc.empty:
            return {"avg_lift": 1.0, "note": "去年数据不足"}

        merged = last_year_actual.merge(last_year_fc, on="ds", suffixes=("_actual", "_fc"))
        merged["lift"] = safe_div(merged["y"], merged["yhat"])

        daily_lifts = {}
        for _, row in merged.iterrows():
            # 映射到今年的同月同日
            this_year_date = row["ds"] + pd.DateOffset(years=1)
            daily_lifts[this_year_date.strftime("%Y-%m-%d")] = round(float(row["lift"]), 3)

        return {
            "avg_lift": round(float(merged["lift"].mean()), 3),
            "peak_lift": round(float(merged["lift"].max()), 3),
            "daily_lifts": daily_lifts,
            "note": "基于去年同期的实际/Prophet比值",
        }

    def should_use_llm(self, special_events: List[Dict] = None) -> bool:
        """判断是否需要 LLM 介入（仅在特殊事件时）"""
        if not special_events:
            return False
        for ev in special_events:
            for trigger in self.config.llm_trigger_conditions:
                if trigger in str(ev):
                    return True
        return False

    def get_agriculture_adjustments(
        self,
        l2_series: Dict[str, pd.DataFrame],
        df_actual: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
    ) -> Dict[str, Dict]:
        """
        一站式获取所有农商品类序列的季节性调整因子
        返回: {系列名: {daily_lifts: {...}, avg_lift: ...}}
        """
        agri_series = self.identify_agri_series(l2_series)

        results = {}
        for name, _ in agri_series.items():
            results[name] = self.compute_seasonal_lift(df_actual, prophet_forecast, name)

        return results
