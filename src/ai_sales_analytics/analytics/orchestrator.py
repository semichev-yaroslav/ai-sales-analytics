from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ai_sales_analytics.analytics.insights.heuristic import HeuristicInsightEngine
from ai_sales_analytics.analytics.insights.llm import LLMInsightEngine
from ai_sales_analytics.analytics.metrics.funnel import FunnelAnalyticsService
from ai_sales_analytics.analytics.metrics.intents import IntentAnalyticsService
from ai_sales_analytics.analytics.metrics.operational import OperationalMetricsService
from ai_sales_analytics.analytics.metrics.quality import QualityAnalyticsService
from ai_sales_analytics.analytics.models import DailyAnalyticsReport
from ai_sales_analytics.config import Settings
from ai_sales_analytics.db.contracts import DataBundle
from ai_sales_analytics.db.repository import AnalyticsRepository
from ai_sales_analytics.time_utils import TimeWindow, daily_window, lookback_window


@dataclass(slots=True)
class AnalyticsResult:
    report: DailyAnalyticsReport
    bundle: DataBundle
    day_window: TimeWindow
    history_window: TimeWindow


class AnalyticsOrchestrator:
    def __init__(self, repository: AnalyticsRepository, settings: Settings):
        self.repository = repository
        self.settings = settings

        self.operational_service = OperationalMetricsService()
        self.funnel_service = FunnelAnalyticsService(stuck_stage_days=settings.stuck_stage_days)
        self.intent_service = IntentAnalyticsService(
            low_confidence_threshold=settings.low_confidence_threshold,
            lost_lead_inactivity_hours=settings.lost_lead_inactivity_hours,
        )
        self.quality_service = QualityAnalyticsService(low_confidence_threshold=settings.low_confidence_threshold)
        self.heuristic_insights = HeuristicInsightEngine()

        self.llm_engine: LLMInsightEngine | None = None
        if settings.enable_llm_insights and settings.openai_api_key:
            self.llm_engine = LLMInsightEngine(api_key=settings.openai_api_key, model=settings.openai_model)

    def run_daily(self, report_date: date) -> AnalyticsResult:
        day = daily_window(report_date, self.settings.default_timezone)
        history = lookback_window(report_date, self.settings.default_timezone, self.settings.lookback_days)

        bundle = self.repository.fetch_bundle(history.start, day.end)

        kpi = self.operational_service.calculate(
            leads=bundle.leads,
            messages=bundle.messages,
            ai_runs=bundle.ai_runs,
            bookings=bundle.bookings,
            followups=bundle.followups,
            stage_events=bundle.stage_events,
            day_start=day.start,
            day_end=day.end,
        )

        funnel = self.funnel_service.calculate(
            leads=bundle.leads,
            messages=bundle.messages,
            ai_runs=bundle.ai_runs,
            bookings=bundle.bookings,
            stage_events=bundle.stage_events,
            day_start=day.start,
            day_end=day.end,
        )

        intents = self.intent_service.calculate(
            leads=bundle.leads,
            messages=bundle.messages,
            ai_runs=bundle.ai_runs,
            bookings=bundle.bookings,
            day_start=day.start,
            day_end=day.end,
        )

        quality = self.quality_service.calculate(
            messages=bundle.messages,
            ai_runs=bundle.ai_runs,
            bookings=bundle.bookings,
            stage_events=bundle.stage_events,
            followups=bundle.followups,
            day_start=day.start,
            day_end=day.end,
        )

        report = DailyAnalyticsReport(
            report_date=report_date.isoformat(),
            timezone=self.settings.default_timezone,
            kpi=kpi,
            funnel=funnel,
            intents=intents,
            quality=quality,
            insights=self.heuristic_insights.generate(kpi=kpi, funnel=funnel, intents=intents, quality=quality),
            charts=[],
        )

        if self.llm_engine:
            payload = {
                "kpi": report.kpi.model_dump(),
                "funnel": report.funnel.model_dump(),
                "intents": report.intents.model_dump(),
                "quality": report.quality.model_dump(),
                "heuristic_findings": report.insights.key_findings,
                "heuristic_risks": report.insights.risk_flags,
            }
            report.insights.llm_summary = self.llm_engine.generate_summary(payload)

        return AnalyticsResult(report=report, bundle=bundle, day_window=day, history_window=history)
