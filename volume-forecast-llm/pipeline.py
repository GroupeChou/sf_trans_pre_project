"""收件量LLM推理预测 — 主编排 Pipeline"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable

import pandas as pd

from .config import (
    ProphetConfig,
    DataConfig,
    PromotionConfig,
    LLMConfig,
    AgricultureConfig,
)
from .data_prep import DataPreparator
from .prophet_baseline import ProphetBaseline
from .promotion_search import PromotionCollector
from .promotion_lift import PromotionLiftAnalyzer
from .llm_reasoning import LLMReasoningEngine
from .agriculture import AgricultureAnalyzer
from .forecast_assembly import ForecastAssembler
from .utils import logger, to_json


class VolumeForecastPipeline:
    """
    收件量 LLM 推理预测主编排

    完整流程：
      Data → Prophet基线 → 促销搜索 → 历史增幅 → LLM推理 → 组装 → 输出
    """

    def __init__(
        self,
        prophet_cfg: ProphetConfig = None,
        data_cfg: DataConfig = None,
        promo_cfg: PromotionConfig = None,
        llm_cfg: LLMConfig = None,
        agri_cfg: AgricultureConfig = None,
    ):
        self.prophet_cfg = prophet_cfg or ProphetConfig()
        self.data_cfg = data_cfg or DataConfig()
        self.promo_cfg = promo_cfg or PromotionConfig()
        self.llm_cfg = llm_cfg or LLMConfig()
        self.agri_cfg = agri_cfg or AgricultureConfig()

        # 模块
        self.data_prep = DataPreparator(self.data_cfg)
        self.prophet = ProphetBaseline(self.prophet_cfg)
        self.promo_collector = PromotionCollector(self.promo_cfg)
        self.lift_analyzer = PromotionLiftAnalyzer()
        self.llm_engine = LLMReasoningEngine(self.llm_cfg)
        self.agri_analyzer = AgricultureAnalyzer(self.agri_cfg)
        self.assembler = ForecastAssembler()

        # LLM 回调（外部注入）
        self._llm_callback: Optional[Callable] = None

        # 状态
        self._state: Dict = {}

    def set_llm_callback(self, callback: Callable[[str], str]):
        """
        注入 LLM 调用回调

        WorkBuddy 环境：不需要设置（在 skill 内对话即 LLM）
        外部环境：callback(prompt: str) -> response: str
        """
        self._llm_callback = callback

    # ================================================================
    # 分步执行
    # ================================================================

    def step1_load_data(self, data_path: str) -> dict:
        """Step 1: 加载 & 聚合数据"""
        logger.info("=" * 60)
        logger.info("Step 1: 数据加载与聚合")
        logger.info("=" * 60)

        df = self.data_prep.load_and_validate(data_path)
        df_all, series_dict = self.data_prep.aggregate_to_daily(df)

        self._state["df_all"] = df_all
        self._state["series_dict"] = series_dict
        self._state["l1_series"] = series_dict["L1"]
        self._state["l2_series"] = series_dict["L2"]

        return {
            "total_rows": len(df),
            "date_range": f"{df['date'].min()} ~ {df['date'].max()}",
            "l1_count": len(series_dict["L1"]),
            "l2_count": len(series_dict["L2"]),
        }

    def step2_prophet_baseline(self, forecast_days: int = 60) -> dict:
        """Step 2: Prophet 基线预测"""
        logger.info("=" * 60)
        logger.info("Step 2: Prophet 基线预测")
        logger.info("=" * 60)

        all_series = {}
        all_series.update(self._state["l1_series"])
        all_series.update(self._state["l2_series"])

        results = self.prophet.train_all(all_series, forecast_days)

        l1_results = {k: v for k, v in results.items() if k in self._state["l1_series"]}
        l2_results = {k: v for k, v in results.items() if k in self._state["l2_series"]}

        # 全量汇总
        total_baseline = self.prophet.aggregate_forecast(l1_results, l2_results)
        summary = self.prophet.get_forecast_summary(total_baseline, forecast_days)

        self._state["l1_results"] = l1_results
        self._state["l2_results"] = l2_results
        self._state["total_baseline"] = total_baseline
        self._state["baseline_summary"] = summary

        return summary

    def step3_collect_promotions(self, force_refresh: bool = False) -> List[Dict]:
        """Step 3: 促销事件采集"""
        logger.info("=" * 60)
        logger.info("Step 3: 促销事件采集")
        logger.info("=" * 60)

        events = self.promo_collector.search_promotions(force_refresh=force_refresh)
        comparison = self.promo_collector.compare_with_last_year(events)

        self._state["promotion_events"] = events
        self._state["calendar_comparison"] = comparison

        return events

    def step4_compute_lifts(self) -> Dict:
        """Step 4: 历史促销增幅计算"""
        logger.info("=" * 60)
        logger.info("Step 4: 历史促销增幅计算")
        logger.info("=" * 60)

        events = self._state.get("promotion_events", [])
        total_baseline = self._state.get("total_baseline")
        df_all = self._state.get("df_all")

        if events and total_baseline is not None and df_all is not None:
            lifts = self.lift_analyzer.compute_historical_lifts(df_all, total_baseline, events)
            self._state["historical_lifts"] = lifts
            self._state["historical_lifts_text"] = self.lift_analyzer.format_for_llm_context()
        else:
            self._state["historical_lifts"] = {}
            self._state["historical_lifts_text"] = "无历史增幅数据"

        return self._state["historical_lifts"]

    def step5_llm_reasoning(
        self,
        additional_context: str = "",
        forecast_days: int = 60,
    ) -> Dict:
        """Step 5: LLM 推理调整因子"""
        logger.info("=" * 60)
        logger.info("Step 5: LLM 推理调整因子")
        logger.info("=" * 60)

        prep = self.llm_engine.prepare_for_llm(
            promotion_events=self._state.get("promotion_events", []),
            calendar_comparison=self._state.get("calendar_comparison", {}),
            historical_lifts_text=self._state.get("historical_lifts_text", ""),
            prophet_baseline=self._state.get("total_baseline", pd.DataFrame()),
            additional_context=additional_context,
            forecast_days=forecast_days,
        )

        prompt = prep["prompt"]

        # LLM 调用
        if self._llm_callback:
            llm_response = self._llm_callback(prompt)
        else:
            # WorkBuddy skill 模式：prompt 由外层对话处理
            logger.info("LLM prompt 已就绪，等待外层调用")
            self._state["llm_prep"] = prep
            return {"status": "pending_llm_call", "prompt": prompt}

        # 解析响应
        result = prep["parse_fn"](llm_response)

        if "error" not in result:
            result["adjustments"] = prep["validate_fn"](result.get("adjustments", []))

        self._state["llm_result"] = result
        return result

    def process_llm_response(self, llm_response: str) -> Dict:
        """
        处理 LLM 响应（用于 WorkBuddy skill 模式，由外层对话传入 LLM 输出）
        """
        prep = self._state.get("llm_prep")
        if not prep:
            raise RuntimeError("请先执行 step5_llm_reasoning()")

        result = prep["parse_fn"](llm_response)

        if "error" not in result:
            result["adjustments"] = prep["validate_fn"](result.get("adjustments", []))

        self._state["llm_result"] = result
        return result

    def step6_agriculture(self) -> Dict:
        """Step 6: 农商季节性效应"""
        logger.info("=" * 60)
        logger.info("Step 6: 农商季节性效应")
        logger.info("=" * 60)

        agri_adjustments = self.agri_analyzer.get_agriculture_adjustments(
            l2_series=self._state.get("l2_series", {}),
            df_actual=self._state.get("df_all", pd.DataFrame()),
            prophet_forecast=self._state.get("total_baseline", pd.DataFrame()),
        )

        self._state["agri_adjustments"] = agri_adjustments
        return agri_adjustments

    def step7_assemble_and_output(
        self,
        forecast_days: int = 60,
        output_dir: str = "./output",
    ) -> Dict:
        """Step 7: 组装最终预测 & 输出"""
        logger.info("=" * 60)
        logger.info("Step 7: 组装 & 输出")
        logger.info("=" * 60)

        os.makedirs(output_dir, exist_ok=True)

        llm_result = self._state.get("llm_result", {})
        adjustments = llm_result.get("adjustments", [])
        agri_adj = self._state.get("agri_adjustments", {})

        # 组装 L1 + L2
        l1_adjusted = {}
        l2_adjusted = {}

        for name, fc in self._state.get("l1_results", {}).items():
            l1_adjusted[name] = self.assembler.apply_adjustments(fc, adjustments, agri_adj)

        for name, fc in self._state.get("l2_results", {}).items():
            l2_adjusted[name] = self.assembler.apply_adjustments(fc, adjustments, agri_adj)

        # 汇总全量
        total_forecast = self.assembler.aggregate_to_total(l1_adjusted, l2_adjusted)

        # 生成报告
        report_path = os.path.join(output_dir, "forecast_report.md")
        self.assembler.generate_report(
            total_forecast,
            self._state.get("baseline_summary", {}),
            llm_result,
            report_path,
        )

        # 导出 JSON
        json_path = os.path.join(output_dir, "forecast_result.json")
        self.assembler.export_forecast_json(total_forecast, llm_result, json_path)

        # 导出 CSV
        csv_path = os.path.join(output_dir, "forecast_daily.csv")
        fc_export = total_forecast.tail(forecast_days).copy()
        fc_export["ds"] = fc_export["ds"].dt.strftime("%Y-%m-%d")
        fc_export.to_csv(csv_path, index=False)

        self._state["total_forecast"] = total_forecast
        self._state["l1_adjusted"] = l1_adjusted
        self._state["l2_adjusted"] = l2_adjusted

        return {
            "output_dir": output_dir,
            "files": {
                "report": report_path,
                "json": json_path,
                "csv": csv_path,
            },
            "summary": {
                "total_volume_60d": round(float(total_forecast["total_forecast"].tail(forecast_days).sum()), 0),
                "avg_daily": round(float(total_forecast["total_forecast"].tail(forecast_days).mean()), 0),
            },
        }

    # ================================================================
    # 一键执行
    # ================================================================
    def run(
        self,
        data_path: str,
        forecast_days: int = 60,
        output_dir: str = "./output",
        additional_context: str = "",
        force_refresh_promos: bool = False,
    ) -> Dict:
        """
        一键执行完整预测流程

        注意：WorkBuddy skill 模式下，
        本方法执行到 step5 时会暂停，等待外层 LLM 调用完成。
        返回的 result 中包含 prompt 供外层使用。

        外部环境（已注入 llm_callback）：
        本方法会自动完成全部 7 步。
        """
        logger.info("=" * 70)
        logger.info(f"  收件量 LLM 推理预测 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info("=" * 70)

        # Step 1-2: 数据 + 基线（无 LLM 依赖）
        self.step1_load_data(data_path)
        self.step2_prophet_baseline(forecast_days)

        # Step 3-4: 促销 + 增幅（无 LLM 依赖，但可能需要外部搜索工具）
        self.step3_collect_promotions(force_refresh=force_refresh_promos)
        self.step4_compute_lifts()

        # Step 5: LLM 推理
        llm_raw = self.step5_llm_reasoning(additional_context, forecast_days)

        # 如果 LLM 未完成（WorkBuddy skill 模式），返回等待状态
        if llm_raw.get("status") == "pending_llm_call":
            # 保存当前状态
            self._state["_pending"] = {
                "forecast_days": forecast_days,
                "output_dir": output_dir,
            }
            return {
                "status": "awaiting_llm",
                "prompt": llm_raw["prompt"],
                "message": "请将上方 prompt 输入到 LLM 中，然后将 LLM 的响应传给 process_llm_response() 方法继续执行。",
            }

        # Step 6-7: 农商 + 组装输出
        self.step6_agriculture()
        output = self.step7_assemble_and_output(forecast_days, output_dir)

        # 清理中间状态
        self._state.pop("_pending", None)
        self._state.pop("llm_prep", None)

        return {"status": "completed", **output}

    def resume_after_llm(self, llm_response: str) -> Dict:
        """
        收到 LLM 响应后继续执行（用于 WorkBuddy skill 模式）
        """
        pending = self._state.pop("_pending", {})
        if not pending:
            raise RuntimeError("没有待处理的 LLM 调用。请先执行 run()。")

        forecast_days = pending.get("forecast_days", 60)
        output_dir = pending.get("output_dir", "./output")

        # 处理 LLM 响应
        self.process_llm_response(llm_response)

        # 继续执行
        self.step6_agriculture()
        output = self.step7_assemble_and_output(forecast_days, output_dir)

        self._state.pop("llm_prep", None)

        return {"status": "completed", **output}

    def get_state_summary(self) -> Dict:
        """获取当前 pipeline 状态摘要"""
        return {
            "has_data": "df_all" in self._state,
            "has_baseline": "total_baseline" in self._state,
            "has_promotions": "promotion_events" in self._state,
            "has_lifts": "historical_lifts" in self._state,
            "has_llm_result": "llm_result" in self._state,
            "has_forecast": "total_forecast" in self._state,
            "l1_count": len(self._state.get("l1_series", {})),
            "l2_count": len(self._state.get("l2_series", {})),
            "promotion_event_count": len(self._state.get("promotion_events", [])),
            "is_awaiting_llm": "_pending" in self._state,
        }
