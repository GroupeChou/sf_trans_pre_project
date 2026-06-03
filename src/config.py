"""Core configuration management for the Prediction Agent Platform."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PREDICTION_",
    )

    # App
    app_name: str = "transit-site-prediction-agent-platform"
    version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prediction"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_api_key: str = ""
    llm_api_base: str = "https://api.anthropic.com"
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

    # Token budgets per prediction
    token_budget_quick: int = 500       # Quick mode: ~300 tokens
    token_budget_standard: int = 1500   # Standard: ~1100 tokens
    token_budget_deep: int = 3000       # Deep: ~2600 tokens

    # Skill execution
    skill_timeout_seconds: int = 30
    skill_max_retries: int = 1
    max_parallel_skills: int = 10

    # Debate
    debate_max_rounds: int = 3
    debate_disagreement_threshold: float = 0.20
    debate_budget_tokens: int = 2000

    # HITL
    hitl_disagreement_threshold: float = 0.50
    hitl_high_impact_threshold: float = 0.35

    # Difficulty scoring (DAAO)
    difficulty_data_weight: float = 0.30
    difficulty_event_weight: float = 0.25
    difficulty_volatility_weight: float = 0.25
    difficulty_rarity_weight: float = 0.20

    # Thompson Sampling
    thompson_decay_factor: float = 0.92
    thompson_min_sigma: float = 0.05
    thompson_cold_start_samples: int = 30

    # Caching
    evidence_cache_ttl_seconds: int = 300
    semantic_cache_enabled: bool = True

    # Multi-tenant
    max_tenants: int = 100
    default_tenant_quota_per_minute: int = 100

    # Audit
    audit_enabled: bool = True
    audit_retention_days: int = 365

    # Paths
    skills_dir: Path = Path("src/skills")
    data_dir: Path = Path("data")


settings = Settings()
