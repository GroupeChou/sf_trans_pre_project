"""预测组装模块 — 将各因子应用到基线预测，输出最终结果"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

from .utils import logger


class ForecastAssembler:
    """组装最终预测：基线 × 促销因子 × 农商因子"""

    def apply_adjustments(
        self,
        prophet_forecast: pd.DataFrame,
        promotion_adjustments: List[Dict],
        agriculture_adjustments: Dict[str, Dict] = None,
    ) -> pd.DataFrame:
        """
        将 LLM 推理的调整因子应用到 Prophet 基线

        Args:
            prophet_forecast: Prophet 输出 [ds, yhat, yhat_lower, yhat_upper, series_name]
            promotion_adjustments: LLM 输出的调整因子列表
            agriculture_adjustments: 农商调整因子 {series_name: {daily_lifts: {}}}

        Returns:
            增强后的预测 DataFrame [ds, yhat, adjusted_yhat, promo_factor, agri_factor, final]
        """
        result = prophet_forecast.copy()

        # 1. 初始化因子列
        result["promo_factor"] = 1.0
        result["agri_factor"] = 1.0

        # 2. 应用促销调整因子
        for adj in promotion_adjustments:
            factors = adj.get("daily_factors", {})
            for date_str, factor in factors.items():
                try:
                    mask = result["ds"] == pd.Timestamp(date_str)
                    result.loc[mask, "promo_factor"] = float(factor)
                except Exception:
                    continue

        # 3. 应用农商调整因子
        if agriculture_adjustments:
            for series_name, agri_info in agriculture_adjustments.items():
                daily_lifts = agri_info.get("daily_lifts", {})
                series_mask = result["series_name"] == series_name
                for date_str, lift in daily_lifts.items():
                    try:
                        mask = series_mask & (result["ds"] == pd.Timestamp(date_str))
                        result.loc[mask, "agri_factor"] = float(lift)
                    except Exception:
                        continue

        # 4. 计算最终预测
        result["final"] = result["yhat"] * result["promo_factor"] * result["agri_factor"]
        result["final_lower"] = result["yhat_lower"] * result["promo_factor"] * result["agri_factor"]
        result["final_upper"] = result["yhat_upper"] * result["promo_factor"] * result["agri_factor"]

        return result

    def aggregate_to_total(
        self,
        l1_adjusted: Dict[str, pd.DataFrame],
        l2_adjusted: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        从 L1（大客户）+ L2（板块×地区）汇总到全量
        """
        all_dfs = []

        for name, df in l1_adjusted.items():
            subset = df[["ds", "final", "final_lower", "final_upper"]].copy()
            subset["source"] = f"L1_{name}"
            all_dfs.append(subset)

        for name, df in l2_adjusted.items():
            subset = df[["ds", "final", "final_lower", "final_upper"]].copy()
            subset["source"] = f"L2_{name}"
            all_dfs.append(subset)

        combined = pd.concat(all_dfs, ignore_index=True)
        total = combined.groupby("ds").agg({
            "final": "sum",
            "final_lower": "sum",
            "final_upper": "sum",
        }).reset_index()

        total.columns = ["ds", "total_forecast", "total_lower", "total_upper"]
        return total

    def generate_report(
        self,
        total_forecast: pd.DataFrame,
        baseline_summary: dict,
        llm_reasoning: dict,
        output_path: str,
    ) -> str:
        """生成可读的 Markdown 预测报告"""
        fc = total_forecast.tail(60)

        lines = [
            "# 收件量预测报告",
            f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**预测周期**: {fc['ds'].min().strftime('%Y-%m-%d')} ~ {fc['ds'].max().strftime('%Y-%m-%d')}",
            "",
            "## 总体预测",
            f"- 60天总收件量: **{fc['total_forecast'].sum():,.0f}** 件",
            f"- 日均收件量: **{fc['total_forecast'].mean():,.0f}** 件",
            f"- 最高单日: **{fc['total_forecast'].max():,.0f}** ({fc.loc[fc['total_forecast'].idxmax(), 'ds'].strftime('%Y-%m-%d')})",
            f"- 最低单日: **{fc['total_forecast'].min():,.0f}** ({fc.loc[fc['total_forecast'].idxmin(), 'ds'].strftime('%Y-%m-%d')})",
            "",
            "## Prophet 基线摘要",
            f"- 日均基线: {baseline_summary.get('avg_daily', 'N/A'):,.0f} 件",
            f"- 趋势方向: {baseline_summary.get('trend', 'N/A')}",
            "",
            "## LLM 推理摘要",
        ]

        if isinstance(llm_reasoning, dict):
            executive_summary = llm_reasoning.get("executive_summary", "无")
            lines.append(executive_summary)

            adjustments = llm_reasoning.get("adjustments", [])
            if adjustments:
                lines.append("\n### 调整详情")
                lines.append("| 阶段 | 日期范围 | 平均因子 | 置信度 | 说明 |")
                lines.append("|------|---------|---------|--------|------|")
                for adj in adjustments[:10]:
                    factors = adj.get("daily_factors", {})
                    avg_f = np.mean(list(factors.values())) if factors else 1.0
                    lines.append(
                        f"| {adj.get('phase', '')} | {adj.get('date_range', ['', ''])[0]}~{adj.get('date_range', ['', ''])[-1]} "
                        f"| {avg_f:.2f} | {adj.get('confidence', '')} | {adj.get('reasoning', '')[:60]}... |"
                    )

        # 写入文件
        report_text = "\n".join(lines)
        if output_path:
            with open(output_path, "w") as f:
                f.write(report_text)
            logger.info(f"预测报告已保存: {output_path}")

        return report_text

    def export_forecast_json(
        self,
        total_forecast: pd.DataFrame,
        adjustment_detail: dict,
        output_path: str,
    ) -> str:
        """导出结构化 JSON 预测结果"""
        fc = total_forecast.tail(60).copy()
        fc["ds"] = fc["ds"].dt.strftime("%Y-%m-%d")

        daily_values = []
        for _, row in fc.iterrows():
            daily_values.append({
                "date": row["ds"],
                "forecast": round(float(row["total_forecast"]), 0),
                "lower_bound": round(float(row["total_lower"]), 0),
                "upper_bound": round(float(row["total_upper"]), 0),
            })

        result = {
            "generated_at": datetime.now().isoformat(),
            "forecast_horizon": 60,
            "daily_values": daily_values,
            "summary": {
                "total_volume": round(float(fc["total_forecast"].sum()), 0),
                "avg_daily": round(float(fc["total_forecast"].mean()), 0),
                "max_daily": round(float(fc["total_forecast"].max()), 0),
                "min_daily": round(float(fc["total_forecast"].min()), 0),
            },
            "adjustment_detail": adjustment_detail,
        }

        import json
        with open(output_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"结构化预测结果已保存: {output_path}")
        return output_path
