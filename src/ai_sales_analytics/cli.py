from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import typer
import uvicorn

from ai_sales_analytics.bootstrap import get_pipeline, get_settings
from ai_sales_analytics.logging_config import setup_logging
from ai_sales_analytics.scheduler.jobs import DailyScheduler

app = typer.Typer(help="AI Sales Analytics CLI")


@app.command("run-daily")
def run_daily(
    report_date: str | None = typer.Option(default=None, help="ISO date: YYYY-MM-DD"),
    send_telegram: bool = typer.Option(default=False, help="Send telegram summary after report generation"),
) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    if report_date:
        target_date = date.fromisoformat(report_date)
    else:
        tz = ZoneInfo(settings.default_timezone)
        target_date = datetime.now(tz=tz).date()

    pipeline = get_pipeline()
    result = pipeline.run(report_date=target_date, send_telegram=send_telegram)

    typer.echo(f"Report generated for {target_date.isoformat()}")
    typer.echo(f"JSON: {result.json_path.resolve()}")
    typer.echo(f"HTML: {result.html_path.resolve()}")
    typer.echo(f"Charts: {result.charts_dir.resolve()}")


@app.command("backfill")
def backfill(
    start_date: str = typer.Option(..., help="ISO date: YYYY-MM-DD"),
    end_date: str = typer.Option(..., help="ISO date: YYYY-MM-DD"),
    send_telegram: bool = typer.Option(default=False, help="Send telegram for each day"),
) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise typer.BadParameter("end_date must be >= start_date")

    pipeline = get_pipeline()
    current = start
    while current <= end:
        result = pipeline.run(report_date=current, send_telegram=send_telegram)
        typer.echo(f"Generated {current.isoformat()} -> {result.html_path.resolve()}")
        current += timedelta(days=1)


@app.command("serve")
def serve() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    uvicorn.run(
        "ai_sales_analytics.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


@app.command("scheduler")
def scheduler() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    daily_scheduler = DailyScheduler(pipeline=get_pipeline(), settings=settings)
    daily_scheduler.start()


if __name__ == "__main__":
    app()
