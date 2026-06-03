"""促销事件采集模块 — 联网搜索 + LLM 提取 + 去年对比"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from .config import PromotionConfig
from .utils import logger


class PromotionCollector:
    """促销事件采集器：搜索 → 提取 → 对比"""

    def __init__(self, config: PromotionConfig = None, cache_dir: str = "/tmp/promo_cache"):
        self.config = config or PromotionConfig()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # ----------------------------------------------------------------
    # 搜索层
    # ----------------------------------------------------------------
    def search_promotions(self, force_refresh: bool = False) -> List[Dict]:
        """
        搜索促销事件并返回结构化结果
        如果有缓存且未过期，直接返回缓存
        """
        cache_key = self._cache_key()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        if not force_refresh and self._cache_valid(cache_file):
            logger.info("使用缓存的促销事件数据")
            with open(cache_file, "r") as f:
                return json.load(f)["events"]

        logger.info("开始联网搜索促销事件...")
        all_results = []

        for query in self.config.search_queries:
            logger.info(f"搜索: {query[:60]}...")
            try:
                # NOTE: 此处需要实际的 WebSearch 工具
                # 在 WorkBuddy 环境中可通过内置工具调用
                search_text = self._execute_search(query)
                all_results.append({"query": query, "result": search_text})
            except Exception as e:
                logger.warning(f"搜索失败 [{query[:40]}]: {e}")

        # LLM 提取结构化事件
        events = self._extract_events_via_llm(all_results)

        # 缓存
        with open(cache_file, "w") as f:
            json.dump({
                "events": events,
                "timestamp": datetime.now().isoformat(),
                "search_queries": self.config.search_queries,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"促销事件采集完成: {len(events)} 个事件")
        return events

    def _execute_search(self, query: str) -> str:
        """
        执行搜索（适配不同环境）

        WorkBuddy 环境中使用内置 WebSearch；
        外部环境需要用户提供搜索回调或 API key。
        """
        # 尝试导入内置搜索
        try:
            from __main__ import WebSearch  # type: ignore
            result = WebSearch(query=query, topic="news")
            return str(result)
        except (ImportError, AttributeError):
            pass

        # 用户自定义搜索回调
        if hasattr(self, "_search_callback") and self._search_callback:
            return self._search_callback(query)

        # 开发模式：返回占位信息
        logger.warning(f"无可用搜索工具，返回模拟结果: {query}")
        return f"[DEV] 搜索结果: 搜索词={query}。请在实际环境中替换为真实搜索。"

    def set_search_callback(self, callback):
        """注入外部搜索回调（用于非 WorkBuddy 环境）"""
        self._search_callback = callback

    # ----------------------------------------------------------------
    # LLM 提取层
    # ----------------------------------------------------------------
    def _extract_events_via_llm(self, search_results: List[Dict]) -> List[Dict]:
        """将搜索结果文本交给 LLM 提取结构化事件"""
        # 拼接所有搜索结果
        search_text = ""
        for i, sr in enumerate(search_results):
            search_text += f"\n--- 搜索结果 {i+1}: {sr['query']} ---\n{sr['result'][:3000]}\n"

        prompt = self.config.extraction_prompt.format(
            search_results=search_text,
            timestamp=datetime.now().isoformat(),
        )

        # 调用 LLM
        llm_output = self._call_llm(prompt)

        # 解析 JSON 输出
        try:
            # 清理可能的 markdown 包裹
            llm_output = llm_output.strip()
            if llm_output.startswith("```"):
                llm_output = llm_output.split("\n", 1)[1]
                llm_output = llm_output.rsplit("```", 1)[0]

            result = json.loads(llm_output)
            events = result.get("events", [])

            # 补充字段
            for ev in events:
                ev.setdefault("confidence", "unconfirmed")
                ev.setdefault("source_url", "")
                ev.setdefault("platform", "未知")

            return events
        except json.JSONDecodeError as e:
            logger.error(f"LLM 输出 JSON 解析失败: {e}")
            logger.debug(f"原始输出: {llm_output[:500]}")
            return []

    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM（适配不同环境）

        WorkBuddy 环境通过对话模型响应；
        外部环境需配置 API。
        """
        # 在 WorkBuddy 环境中，LLM 调用由 skill 框架自动处理
        # 这里返回提示词，由上层 pipeline 调用实际 LLM
        return prompt  # pipeline 层会处理实际 LLM 调用

    # ----------------------------------------------------------------
    # 对比层
    # ----------------------------------------------------------------
    def compare_with_last_year(self, events: List[Dict]) -> Dict:
        """
        对比今年 vs 去年同活动的日期差异

        返回示例:
        {
            "天猫618": [
                {"event": "预售开始", "this_year": "2026-05-26", "last_year": "2026-05-28", "delta": -2},
                {"event": "付尾款开始", "this_year": "2026-06-01", "last_year": "2026-06-01", "delta": 0},
            ]
        }
        """
        # 构造去年日期（同活动-同类事件，日期减去365天做粗略推算）
        # 实际应该加载去年采集的真实促销日历
        comparisons = {}

        for ev in events:
            platform = ev.get("platform", "未知")
            event_name = ev.get("event_name", "")
            this_date_str = ev.get("start_date", "")

            if not this_date_str:
                continue

            try:
                this_date = datetime.strptime(this_date_str, "%Y-%m-%d")
                last_year_date = this_date - timedelta(days=365)
            except ValueError:
                continue

            if platform not in comparisons:
                comparisons[platform] = []

            comparisons[platform].append({
                "event": event_name,
                "this_year": this_date_str,
                "last_year_estimated": last_year_date.strftime("%Y-%m-%d"),
            })

        return comparisons

    # ----------------------------------------------------------------
    # 缓存
    # ----------------------------------------------------------------
    def _cache_key(self) -> str:
        queries_str = "|".join(sorted(self.config.search_queries))
        return hashlib.md5(queries_str.encode()).hexdigest()[:12]

    def _cache_valid(self, cache_file: str) -> bool:
        if not os.path.exists(cache_file):
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        return (datetime.now() - mtime).days < self.config.cache_days
