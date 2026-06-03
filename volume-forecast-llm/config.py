"""收件量LLM推理预测系统 — 全局配置"""

from dataclasses import dataclass, field
from typing import List, Dict

# ============================================================
# Prophet 基线配置
# ============================================================
@dataclass
class ProphetConfig:
    growth: str = "linear"
    yearly_seasonality: bool = True
    weekly_seasonality: bool = True
    daily_seasonality: bool = False
    changepoint_prior_scale: float = 0.05
    seasonality_mode: str = "multiplicative"
    seasonality_prior_scale: float = 10.0
    holidays_prior_scale: float = 10.0
    interval_width: float = 0.80  # 80% 置信区间

    # 中国假期扩展窗口（物流场景假期效应比日历假期更长）
    holiday_windows: Dict[str, tuple] = field(default_factory=lambda: {
        "春节": (-7, 7),
        "国庆节": (-2, 2),
        "劳动节": (-1, 1),
        "端午节": (-1, 1),
        "中秋节": (-1, 1),
        "清明节": (-1, 1),
        "元旦": (-1, 1),
    })

    # 调休工作日 — 这些日期虽然标注为周末但实际是工作日
    workday_override_enabled: bool = True


# ============================================================
# 数据配置
# ============================================================
@dataclass
class DataConfig:
    # 输入列名映射
    date_col: str = "date"
    customer_col: str = "customer"
    segment_col: str = "segment"
    region_col: str = "region"
    volume_col: str = "volume"

    # 聚合策略
    top_n_customers: int = 30              # 大客户单独建模数量
    top_customer_threshold: float = 0.70   # 大客户覆盖件量占比

    # 中小客户聚合粒度
    min_daily_for_prophet: int = 100       # 日均件量低于此值的序列不单独建模

    # 历史数据最小年限
    min_years_history: int = 2


# ============================================================
# 促销搜索配置
# ============================================================
@dataclass
class PromotionConfig:
    # 搜索关键词列表（每次执行全部搜索）
    search_queries: List[str] = field(default_factory=lambda: [
        "2026年天猫618活动时间 预售 付尾款 现货开售",
        "2026年天猫双11活动节奏 第一波预售 第二波现货",
        "2026年淘宝天猫全年营销活动日历 38节 99大促 双12 年货节",
        "2026年聚划算活动日历 品牌团 主题团",
        "2026年天猫618活动规则 预售定金 尾款时间",
        "2026年天猫双11招商规则 活动时间表",
    ])

    # 搜索缓存有效期（天）
    cache_days: int = 3

    # LLM 提取 Prompt 模板
    extraction_prompt: str = """## 角色
你是电商促销事件提取器。从下方搜索结果中提取天猫/淘宝/聚划算官方促销活动的精确日期。

## 提取规则
1. 只提取官方平台活动（天猫/淘宝/聚划算），不提取商家自营销
2. 必须提取精确日期，没有日期则标注 "date": null, "confidence": "unconfirmed"
3. 活动类型: "预售开始" | "付尾款开始" | "现货开售" | "狂欢日/爆发日" | "返场" | "活动结束"
4. 每个活动输出一个独立事件对象
5. 如果同一个活动有多篇来源确认了同一日期，confidence 标记为 "confirmed"

## 搜索结果
{search_results}

## 输出格式（严格JSON，不要```包裹）
{{
  "events": [
    {{
      "platform": "天猫618",
      "event_name": "预售开始",
      "start_date": "2026-05-26",
      "end_date": "2026-05-31",
      "description": "支付定金期",
      "source_url": "来源链接",
      "confidence": "confirmed"
    }}
  ],
  "search_timestamp": "{timestamp}",
  "incompleteness_note": "如信息不完整请在此说明"
}}"""


# ============================================================
# LLM 推理配置
# ============================================================
@dataclass
class LLMConfig:
    # 调整因子范围约束
    min_factor: float = 0.5
    max_factor: float = 3.0
    max_deviation_from_last_year: float = 0.30  # 相比去年最大偏差 ±30%

    # 推理 Prompt 模板
    reasoning_prompt: str = """## 角色
你是物流收件量预测专家。Prophet模型已经生成了基线预测（剔除促销/农商效应后的"自然"收件量）。
你的任务是基于促销事件信息、历史增幅数据和外部上下文，推理每个促销阶段的调整因子。

## 核心公式
最终预测 = Prophet基线 × 调整因子

## 已提供的信息
1. **Prophet基线预测**：未来{forecast_days}天每天的基线件量（trend + weekly + holiday）
2. **今年vs去年促销日历对比**：{calendar_comparison}
3. **历史促销增幅数据**：
{historical_lifts}
4. **额外上下文**：{additional_context}

## 推理任务

### 1. 分析差异
逐条分析今年与去年促销日历的差异，判断每条差异对收件量的影响方向（↑/↓/→）。

### 2. 计算调整因子
对每个促销阶段：
- 起点 = 去年同阶段的实际增幅
- 趋势修正 = 基于近年增幅的变化趋势（年均±X%）
- 日历差异修正 = 基于今年vs去年的日期偏移，修正峰值时间和幅度
- 上下文修正 = 基于经济形势/平台政策/已知客户计划，进一步微调
- 输出每日调整因子数组

### 3. 风险标注
对每个阶段标注置信度和主要风险因素。

## 约束
- 调整因子范围: {min_factor} ~ {max_factor}
- 相比去年同阶段增幅的偏差不超过 {max_deviation_pct}%
- 如果没有足够信息判断变化方向，保守处理（default 1.0）

## 输出格式（严格JSON，不要```包裹）
{{
  "promotion_name": "{promotion_name}",
  "analysis": {{
    "calendar_differences_impact": [
      {{"diff": "预售提前2天", "impact_direction": "up", "magnitude": "mid", "reasoning": "..."}}
    ],
    "trend_assessment": "...",
    "key_uncertainties": ["..."]
  }},
  "adjustments": [
    {{
      "phase": "预售期",
      "date_range": ["2026-05-26", "2026-05-31"],
      "daily_factors": {{"2026-05-26": 1.09, "2026-05-27": 1.08}},
      "reasoning": "...",
      "confidence": "high|medium|low",
      "risk_factors": ["..."]
    }}
  ],
  "executive_summary": "..."
}}"""


# ============================================================
# 农商特产配置
# ============================================================
@dataclass
class AgricultureConfig:
    # 农商品类
    agri_segments: List[str] = field(default_factory=lambda: [
        "生鲜", "农产品", "食品", "海鲜水产", "茶叶"
    ])

    # 各农商品类旺季（大致月份）
    seasonal_periods: Dict[str, tuple] = field(default_factory=lambda: {
        "大闸蟹": ("09-15", "12-31"),
        "春茶": ("03-01", "05-15"),
        "荔枝": ("05-01", "06-30"),
        "月饼": ("08-01", "09-30"),
        "年货": ("12-15", "01-31"),
    })

    # 农商效应 LLM 使用场景（仅在以下情况才调用 LLM）
    llm_trigger_conditions: List[str] = field(default_factory=lambda: [
        "开捕日期变动 > 3天",
        "产量预估变动 > 20%",
        "新增农商品类",
    ])
