from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ai_sales_analytics.analytics.models import DailyAnalyticsReport
from ai_sales_analytics.analytics.orchestrator import AnalyticsOrchestrator
from ai_sales_analytics.config import Settings
from ai_sales_analytics.reporting.report_writer import ReportWriter
from ai_sales_analytics.reporting.summary import build_telegram_summary
from ai_sales_analytics.reporting.telegram import TelegramDelivery
from ai_sales_analytics.visualization.charts import ChartBuilder

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    report: DailyAnalyticsReport
    json_path: Path
    html_path: Path
    charts_dir: Path


class DailyAnalyticsPipeline:
    def __init__(self, orchestrator: AnalyticsOrchestrator, settings: Settings):
        self.orchestrator = orchestrator
        self.settings = settings
        self.writer = ReportWriter(settings.reports_dir)

    def run(self, report_date: date, send_telegram: bool | None = None) -> PipelineResult:
        analytics_result = self.orchestrator.run_daily(report_date)
        daily_dir = self.writer.prepare_daily_dir(report_date.isoformat())
        charts_dir = daily_dir / "charts"

        chart_builder = ChartBuilder(charts_dir)
        charts = chart_builder.build(
            report=analytics_result.report,
            bundle=analytics_result.bundle,
            history_start=analytics_result.history_window.start,
            day_end=analytics_result.day_window.end,
        )
        analytics_result.report.charts = charts

        json_path = self.writer.write_json(analytics_result.report, daily_dir)
        html_path = self.writer.write_html(analytics_result.report, daily_dir)

        should_send = send_telegram if send_telegram is not None else self.settings.send_telegram_report
        if should_send and self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            self._send_telegram(analytics_result.report)

        return PipelineResult(
            report=analytics_result.report,
            json_path=json_path,
            html_path=html_path,
            charts_dir=charts_dir,
        )

    def _send_telegram(self, report: DailyAnalyticsReport) -> None:
        try:
            delivery = TelegramDelivery(
                bot_token=self.settings.telegram_bot_token or "",
                chat_id=self.settings.telegram_chat_id or "",
            )
            delivery.send_summary(build_telegram_summary(report))
            for chart in report.charts[:3]:
                delivery.send_chart(Path(chart.file_path), caption=chart.chart_name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Telegram delivery failed: %s", exc)
