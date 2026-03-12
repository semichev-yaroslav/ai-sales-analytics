from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from ai_sales_analytics.bootstrap import get_pipeline, get_settings
from ai_sales_analytics.config import Settings

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/analytics/daily")
def get_daily_analytics(
    report_date: date | None = Query(default=None, description="ISO date, e.g. 2026-03-12"),
    send_telegram: bool = Query(default=False),
    pipeline=Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    if report_date is None:
        tz = ZoneInfo(settings.default_timezone)
        report_date = datetime.now(tz=tz).date()

    result = pipeline.run(report_date=report_date, send_telegram=send_telegram)

    return {
        "report": result.report.model_dump(),
        "artifacts": {
            "json": str(result.json_path.resolve()),
            "html": str(result.html_path.resolve()),
            "charts_dir": str(result.charts_dir.resolve()),
        },
    }
