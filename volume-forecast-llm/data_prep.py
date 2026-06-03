"""数据准备与聚合模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from .config import DataConfig
from .utils import logger


class DataPreparator:
    """数据加载、清洗、聚合、大客户识别"""

    def __init__(self, config: DataConfig = None):
        self.config = config or DataConfig()

    def load_and_validate(self, data_path: str) -> pd.DataFrame:
        """加载原始数据并做基础校验"""
        logger.info(f"加载数据: {data_path}")

        if data_path.endswith(".csv"):
            df = pd.read_csv(data_path, parse_dates=[self.config.date_col])
        elif data_path.endswith(".parquet"):
            df = pd.read_parquet(data_path)
        else:
            raise ValueError(f"不支持的文件格式: {data_path}")

        # 校验必需列
        required = [self.config.date_col, self.config.volume_col]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"缺少必需列: {missing}")

        # 去重 & 排序
        df = df.drop_duplicates().sort_values(self.config.date_col)
        df[self.config.date_col] = pd.to_datetime(df[self.config.date_col])

        logger.info(f"数据加载完成: {len(df)} 行, {df[self.config.date_col].min()} ~ {df[self.config.date_col].max()}")
        return df

    def aggregate_to_daily(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        按三层粒度分别聚合：
        - L1: 客户级（TOP大客户单独序列）
        - L2: 板块×地区级（中小客户聚合）
        - L3: 全量（L1+L2汇总）
        """
        cfg = self.config

        # ---- 全量日聚合 ----
        df_all = df.groupby(cfg.date_col)[cfg.volume_col].sum().reset_index()
        df_all.columns = ["ds", "y"]

        # ---- 识别大客户 ----
        customer_total = df.groupby(cfg.customer_col)[cfg.volume_col].sum().sort_values(ascending=False)
        total_vol = customer_total.sum()
        cumsum = customer_total.cumsum()
        top_customers = customer_total[cumsum / total_vol <= cfg.top_customer_threshold].index.tolist()
        top_customers = top_customers[:cfg.top_n_customers]

        logger.info(f"识别大客户: {len(top_customers)} 个, 覆盖 {cumsum[top_customers[-1]] / total_vol:.1%} 件量")

        # ---- L1: 大客户日聚合 ----
        l1_series = {}
        for cust in top_customers:
            cust_df = (
                df[df[cfg.customer_col] == cust]
                .groupby(cfg.date_col)[cfg.volume_col]
                .sum()
                .reset_index()
            )
            cust_df.columns = ["ds", "y"]
            l1_series[cust] = cust_df

        # ---- L2: 中小客户按板块×地区聚合 ----
        # 先扣除大客户
        df_small = df[~df[cfg.customer_col].isin(top_customers)]

        l2_series = {}
        if cfg.segment_col in df.columns and cfg.region_col in df.columns:
            groups = df_small.groupby([cfg.segment_col, cfg.region_col])
        elif cfg.segment_col in df.columns:
            groups = df_small.groupby(cfg.segment_col)
        elif cfg.region_col in df.columns:
            groups = df_small.groupby(cfg.region_col)
        else:
            groups = [("其他", df_small)]

        for gkey, gdf in groups:
            if isinstance(gkey, tuple):
                gname = f"{gkey[0]}×{gkey[1]}"
            else:
                gname = str(gkey)

            g_agg = gdf.groupby(cfg.date_col)[cfg.volume_col].sum().reset_index()
            g_agg.columns = ["ds", "y"]

            # 过滤日均量过低的序列
            if len(g_agg) >= 30 and g_agg["y"].mean() >= cfg.min_daily_for_prophet:
                l2_series[gname] = g_agg
            else:
                logger.debug(f"跳过稀疏序列: {gname} (日均 {g_agg['y'].mean():.0f} 件)")

        logger.info(f"序列构建完成: L1={len(l1_series)}, L2={len(l2_series)}")

        return df_all, {"L1": l1_series, "L2": l2_series}

    def prepare_prophet_input(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保数据符合Prophet输入格式: ds, y"""
        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        return df[["ds", "y"]].dropna()

    def split_train_test(self, df: pd.DataFrame, forecast_days: int = 60) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """划分训练集（用于回测验证）"""
        cutoff = df["ds"].max() - pd.Timedelta(days=forecast_days)
        train = df[df["ds"] <= cutoff]
        test = df[df["ds"] > cutoff]
        return train, test
