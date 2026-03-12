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


@router.get("/analytics/dialogs/daily")
def get_daily_dialogs(
    report_date: date | None = Query(default=None, description="ISO date, e.g. 2026-03-12"),
    risk_only: bool = Query(default=False, description="Return only risky dialogs"),
    include_transcript: bool = Query(default=True, description="Include full messages in response"),
    limit: int = Query(default=20, ge=1, le=200),
    pipeline=Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    if report_date is None:
        tz = ZoneInfo(settings.default_timezone)
        report_date = datetime.now(tz=tz).date()

    result = pipeline.orchestrator.run_daily(report_date)
    items = result.report.dialog_review.items

    if risk_only:
        items = [item for item in items if item.risk_score >= 3]

    items = items[:limit]
    payload = []
    for item in items:
        dumped = item.model_dump()
        if not include_transcript:
            dumped.pop("transcript", None)
        payload.append(dumped)

    return {
        "report_date": report_date.isoformat(),
        "timezone": settings.default_timezone,
        "total_dialogs": result.report.dialog_review.total_dialogs,
        "risky_dialogs": result.report.dialog_review.risky_dialogs,
        "returned_dialogs": len(payload),
        "dialogs": payload,
    }
