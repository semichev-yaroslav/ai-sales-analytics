from __future__ import annotations

from fastapi import FastAPI

from ai_sales_analytics.api.routes import router
from ai_sales_analytics.bootstrap import get_settings
from ai_sales_analytics.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title="AI Sales Analytics",
    version="0.1.0",
    description="Production-like analytics backend for AI sales bots",
)
app.include_router(router)
