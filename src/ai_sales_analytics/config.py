from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./bot.db", alias="DATABASE_URL")
    schema_mapping_path: str | None = Field(default="config/schema_mapping.example.yaml", alias="SCHEMA_MAPPING_PATH")

    default_timezone: str = Field(default="Europe/Moscow", alias="DEFAULT_TIMEZONE")
    reports_dir: Path = Field(default=Path("./reports"), alias="REPORTS_DIR")
    lookback_days: int = Field(default=30, alias="LOOKBACK_DAYS")
    lost_lead_inactivity_hours: int = Field(default=48, alias="LOST_LEAD_INACTIVITY_HOURS")
    low_confidence_threshold: float = Field(default=0.55, alias="LOW_CONFIDENCE_THRESHOLD")
    stuck_stage_days: int = Field(default=3, alias="STUCK_STAGE_DAYS")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    send_telegram_report: bool = Field(default=False, alias="SEND_TELEGRAM_REPORT")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    enable_llm_insights: bool = Field(default=False, alias="ENABLE_LLM_INSIGHTS")

    daily_report_cron: str = Field(default="0 20 * * *", alias="DAILY_REPORT_CRON")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )


settings = Settings()
