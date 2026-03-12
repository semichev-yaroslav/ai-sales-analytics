from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ai_sales_analytics.analytics.pipeline import DailyAnalyticsPipeline
from ai_sales_analytics.config import Settings

logger = logging.getLogger(__name__)


class DailyScheduler:
    def __init__(self, pipeline: DailyAnalyticsPipeline, settings: Settings):
        self.pipeline = pipeline
        self.settings = settings

    def start(self) -> None:
        tz = ZoneInfo(self.settings.default_timezone)
        scheduler = BlockingScheduler(timezone=tz)
        trigger = CronTrigger.from_crontab(self.settings.daily_report_cron, timezone=tz)
        scheduler.add_job(self._run_report_job, trigger=trigger, id="daily_sales_analytics", replace_existing=True)

        logger.info("Scheduler started with cron '%s' in timezone '%s'", self.settings.daily_report_cron, tz)
        scheduler.start()

    def _run_report_job(self) -> None:
        tz = ZoneInfo(self.settings.default_timezone)
        report_date = datetime.now(tz=tz).date()
        logger.info("Running scheduled daily report for %s", report_date.isoformat())
        self.pipeline.run(report_date=report_date)
