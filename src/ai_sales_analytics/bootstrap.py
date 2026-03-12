from __future__ import annotations

from functools import lru_cache

from ai_sales_analytics.analytics.orchestrator import AnalyticsOrchestrator
from ai_sales_analytics.analytics.pipeline import DailyAnalyticsPipeline
from ai_sales_analytics.config import Settings, settings
from ai_sales_analytics.db.engine import build_engine
from ai_sales_analytics.db.repository import AnalyticsRepository
from ai_sales_analytics.db.schema_mapping import load_schema_mapping


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return settings


@lru_cache(maxsize=1)
def get_pipeline() -> DailyAnalyticsPipeline:
    cfg = get_settings()
    engine = build_engine(cfg.database_url)
    mapping = load_schema_mapping(cfg.schema_mapping_path)
    repository = AnalyticsRepository(engine=engine, mapping=mapping)
    orchestrator = AnalyticsOrchestrator(repository=repository, settings=cfg)
    return DailyAnalyticsPipeline(orchestrator=orchestrator, settings=cfg)
