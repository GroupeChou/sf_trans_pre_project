"""Prophet 基线预测模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from prophet import Prophet
from chinese_calendar import is_workday, is_holiday, get_holiday_detail

from .config import ProphetConfig
from .utils import logger


class ProphetBaseline:
    """多序列 Prophet 基线预测引擎"""

    def __init__(self, config: ProphetConfig = None):
        self.config = config or ProphetConfig()
        self.models: Dict[str, Prophet] = {}
        self.forecasts: Dict[str, pd.DataFrame] = {}

    # ----------------------------------------------------------------
    # 单序列建模
    # ----------------------------------------------------------------
    def _build_model(self, name: str) -> Prophet:
        """构建标准 Prophet 模型"""
        cfg = self.config
        model = Prophet(
            growth=cfg.growth,
            yearly_seasonality=cfg.yearly_seasonality,
            weekly_seasonality=cfg.weekly_seasonality,
            daily_seasonality=cfg.daily_seasonality,
            changepoint_prior_scale=cfg.changepoint_prior_scale,
            seasonality_mode=cfg.seasonality_mode,
            seasonality_prior_scale=cfg.seasonality_prior_scale,
            holidays_prior_scale=cfg.holidays_prior_scale,
            interval_width=cfg.interval_width,
        )
        model.add_country_holidays(country_name="CN")
        return model

    def _add_workday_override(self, model: Prophet, df: pd.DataFrame):
        """处理调休工作日：周末但是工作日的日期"""
        if not self.config.workday_override_enabled:
            return

        dates = pd.date_range(df["ds"].min(), df["ds"].max() + pd.Timedelta(days=90))
        workday_flags = []
        for d in dates:
            if d.weekday() >= 5 and is_workday(d):
                workday_flags.append({"ds": d, "is_workday_override": 1})
            elif d.weekday() < 5 and is_holiday(d):
                workday_flags.append({"ds": d, "is_workday_override": 0})

        if workday_flags:
            override_df = pd.DataFrame(workday_flags)
            df = df.merge(override_df, on="ds", how="left").fillna({"is_workday_override": -1})
            model.add_regressor("is_workday_override")

    def _add_holiday_windows(self, model: Prophet, df: pd.DataFrame):
        """为重要假期添加扩展窗口（物流效应比假期本身更长）"""
        # Prophet 的 add_country_holidays 已经处理了假期当天
        # 这里额外添加假期前后的"影响窗口"
        holidays_cn = []
        for year in range(df["ds"].dt.year.min(), df["ds"].dt.year.max() + 2):
            for date in pd.date_range(f"{year}-01-01", f"{year}-12-31"):
                is_hol, hol_name = get_holiday_detail(date)
                if is_hol and hol_name in self.config.holiday_windows:
                    lower, upper = self.config.holiday_windows[hol_name]
                    for offset in range(lower, upper + 1):
                        if offset != 0:
                            window_date = date + pd.Timedelta(days=offset)
                            holidays_cn.append({
                                "holiday": f"{hol_name}_window",
                                "ds": window_date,
                            })

        if holidays_cn:
            holiday_df = pd.DataFrame(holidays_cn).drop_duplicates(subset=["ds"])
            model.holidays = pd.concat([model.holidays, holiday_df], ignore_index=True)

    def train_single(
        self, df: pd.DataFrame, name: str, forecast_days: int = 60
    ) -> pd.DataFrame:
        """为单个序列训练 Prophet 并预测"""
        logger.info(f"Prophet 训练: {name} ({len(df)} 行)")

        df = df[["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        df = df.dropna()

        if len(df) < 30:
            logger.warning(f"序列 {name} 数据不足（{len(df)} 行），跳过 Prophet，用历史均值")
            return self._fallback_forecast(df, forecast_days, name)

        model = self._build_model(name)
        self._add_workday_override(model, df)
        self._add_holiday_windows(model, df)

        model.fit(df)

        future = model.make_future_dataframe(periods=forecast_days)
        # 补充调休标记
        future["is_workday_override"] = -1
        for i, row in future.iterrows():
            d = row["ds"]
            if d.weekday() >= 5 and is_workday(d):
                future.at[i, "is_workday_override"] = 1
            elif d.weekday() < 5 and is_holiday(d):
                future.at[i, "is_workday_override"] = 0

        forecast = model.predict(future)
        forecast["series_name"] = name

        self.models[name] = model
        self.forecasts[name] = forecast

        return forecast

    def _fallback_forecast(self, df: pd.DataFrame, days: int, name: str) -> pd.DataFrame:
        """历史均值兜底方案（数据不足时使用）"""
        mean_val = df["y"].mean()
        last_date = df["ds"].max()
        dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days, freq="D")
        result = pd.DataFrame({
            "ds": dates,
            "yhat": mean_val,
            "yhat_lower": mean_val * 0.7,
            "yhat_upper": mean_val * 1.3,
            "series_name": name,
        })
        return result

    # ----------------------------------------------------------------
    # 批量建模（并行）
    # ----------------------------------------------------------------
    def train_all(
        self,
        series_dict: Dict[str, pd.DataFrame],
        forecast_days: int = 60,
        max_workers: int = 4,
    ) -> Dict[str, pd.DataFrame]:
        """并行训练所有序列"""
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.train_single, df, name, forecast_days): name
                for name, df in series_dict.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                    logger.info(f"完成: {name}")
                except Exception as e:
                    logger.error(f"失败: {name} — {e}")
        return results

    # ----------------------------------------------------------------
    # 汇总
    # ----------------------------------------------------------------
    def aggregate_forecast(
        self, l1_results: Dict, l2_results: Dict
    ) -> pd.DataFrame:
        """
        汇总 L1（大客户）+ L2（板块×地区）为全量预测
        返回: DataFrame [ds, yhat, yhat_lower, yhat_upper]
        """
        all_forecasts = []
        for results in [l1_results, l2_results]:
            for name, fc in results.items():
                fc = fc[fc["ds"] > fc["ds"].max() - pd.Timedelta(days=70)]
                fc = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
                fc["source"] = name
                all_forecasts.append(fc)

        combined = pd.concat(all_forecasts, ignore_index=True)
        aggregated = (
            combined.groupby("ds")
            .agg({"yhat": "sum", "yhat_lower": "sum", "yhat_upper": "sum"})
            .reset_index()
        )
        return aggregated

    def get_forecast_summary(self, forecast: pd.DataFrame, days: int = 60) -> dict:
        """生成预测摘要"""
        future = forecast[forecast["ds"] > forecast["ds"].max() - pd.Timedelta(days=days + 5)]
        future = future.tail(days)

        return {
            "horizon_days": days,
            "start_date": future["ds"].min().strftime("%Y-%m-%d"),
            "end_date": future["ds"].max().strftime("%Y-%m-%d"),
            "avg_daily": round(future["yhat"].mean(), 0),
            "total_volume": round(future["yhat"].sum(), 0),
            "min_daily": round(future["yhat"].min(), 0),
            "max_daily": round(future["yhat"].max(), 0),
            "trend_direction": "up" if future["yhat"].iloc[-1] > future["yhat"].iloc[0] else "down",
        }
