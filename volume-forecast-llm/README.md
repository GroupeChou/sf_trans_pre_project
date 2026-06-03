# Volume Forecast LLM — 收件量LLM推理预测

> 物流快递收件量预测智能体系统
> Prophet 基线 + 联网搜索促销 + LLM 推理调整因子 → 60天收件量预测


## 预测公式

```
最终预测(日) = Prophet基线(日) × 促销调整因子(日) × 农商调整因子(日)
```

- **Prophet基线**: 学习趋势 / 周效应 / 假期效应
- **促销调整因子**: LLM推理今年vs去年促销日历差异 + 历史增幅
- **农商调整因子**: 季节性农产品增量

## 目录结构

```
volume-forecast-llm/
├── SKILL.md              # WorkBuddy Skill 定义
├── __init__.py           # 包入口
├── config.py             # 全局配置（Prophet/LLM/搜索/Prompt模板）
├── data_prep.py          # 数据加载、分层聚合、大客户识别
├── prophet_baseline.py   # 多序列并行Prophet训练
├── promotion_search.py   # 促销事件联网搜索 + LLM提取
├── promotion_lift.py     # 历史促销增幅知识库
├── llm_reasoning.py      # LLM推理引擎（构建prompt + 解析输出）
├── agriculture.py        # 农商特产季节性效应
├── forecast_assembly.py  # 预测组装、汇总、报告生成
├── pipeline.py           # 主编排（7步流程）
├── utils.py              # 工具函数
├── requirements.txt      # Python依赖
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 数据格式

输入 CSV 需包含以下列：

| 列名 | 类型 | 说明 |
|------|------|------|
| date | YYYY-MM-DD | 日期 |
| customer | string | 客户名称 |
| segment | string | 板块/品类 |
| region | string | 地区 |
| volume | int | 收件量（件） |

### 3. 运行预测

```python
from volume_forecast_llm import VolumeForecastPipeline

pipeline = VolumeForecastPipeline()

# 一键执行（WorkBuddy skill 模式）
result = pipeline.run(
    data_path="/path/to/historical_data.csv",
    forecast_days=60,
    output_dir="./output",
    additional_context="2026年消费复苏，618预计参与品牌+15%",
)

# 如果返回 awaiting_llm，说明需要先执行 LLM 推理：
if result["status"] == "awaiting_llm":
    # 将 result["prompt"] 输入到 LLM
    llm_response = your_llm_call(result["prompt"])
    # 继续执行
    final = pipeline.resume_after_llm(llm_response)
```

### 4. 分步执行

```python
pipeline.step1_load_data("data.csv")
pipeline.step2_prophet_baseline(60)
pipeline.step3_collect_promotions()
pipeline.step4_compute_lifts()
pipeline.step5_llm_reasoning()
# ... 等待LLM响应 ...
pipeline.step6_agriculture()
pipeline.step7_assemble_and_output(60, "./output")
```

### 5. 输出文件

```
output/
├── forecast_report.md     # 可读预测报告
├── forecast_result.json   # 结构化预测结果
└── forecast_daily.csv     # 每日预测值CSV
```

## 与 Pipeline SOP 的关系

| 本模块 | Pipeline SOP 对应 |
|--------|------------------|
| data_prep.py | F-INPUT 数据获取 |
| prophet_baseline.py | F-PREDICT 预测框架 |
| promotion_search.py | P-RAG 检索增强 |
| llm_reasoning.py | 推理引擎（新增原子组件） |
| agriculture.py | 场景专属模块 |
| forecast_assembly.py | F-OUTPUT 输出 |
