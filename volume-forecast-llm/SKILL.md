---
name: volume-forecast-llm
description: >
  物流收件量 LLM 推理预测系统。基于 Prophet 基线 + 联网搜索促销事件 + LLM 推理调整因子，
  预测未来 60 天分客户/分板块/分地区的每日收件量。适用于快递物流行业的收件量中长期预测场景。
agent_created: true
---

# Volume Forecast LLM — 收件量 LLM 推理预测

## 角色

物流收件量预测专用智能体。基于 Prophet 统计基线 + LLM 事件推理的混合预测架构。

## 核心公式

```
最终预测(日) = Prophet基线(日) × 促销调整因子(日) × 农商调整因子(日)
```

- **Prophet 基线**：学习年增长 / 周效应 / 假期效应
- **促销调整因子**：联网搜索官方促销日期 + LLM 推理今年 vs 去年的增幅差异
- **农商调整因子**：季节性农产品（大闸蟹/茶叶等）的增量

## 适用场景

触发条件（任一满足）：
- 用户提到「收件量预测」「揽件量预测」「volume forecast」
- 用户需要预测未来 N 天（通常 30-90 天）的每日收件量
- 用户询问「618/双11 对收件量的影响」

## 输入格式

```json
{
  "data_path": "/path/to/historical_data.csv",
  "forecast_days": 60,
  "output_path": "/path/to/output",
  "mode": "full" | "baseline_only" | "adjustment_only"
}
```

## 输出

- `forecast_result.json`：结构化预测结果
- `forecast_report.md`：可读预测报告（含归因解释）
- `forecast_chart.png`：预测曲线图

## 依赖

- Python 3.10+
- prophet, pandas, numpy
- chinese-calendar
- matplotlib（可视化）

## 关键 pipeline

1. `pipeline.py` — 完整端到端流程
2. `prophet_baseline.py` — 基线生成（多序列并行）
3. `promotion_search.py` — 促销事件联网获取
4. `llm_reasoning.py` — LLM 调整因子推理
5. `forecast_assembly.py` — 最终预测组装与输出
