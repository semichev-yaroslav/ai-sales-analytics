from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ai_sales_analytics.analytics.models import ChartArtifact, DailyAnalyticsReport
from ai_sales_analytics.db.contracts import DataBundle

logger = logging.getLogger(__name__)
sns.set_theme(style="whitegrid")


class ChartBuilder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        report: DailyAnalyticsReport,
        bundle: DataBundle,
        history_start: datetime,
        day_end: datetime,
    ) -> list[ChartArtifact]:
        artifacts: list[ChartArtifact] = []

        artifacts.append(self._funnel_chart(report))
        artifacts.append(self._stage_distribution_chart(report))
        artifacts.append(self._leads_trend_chart(bundle, history_start, day_end))
        artifacts.append(self._conversion_trend_chart(bundle, history_start, day_end))
        artifacts.append(self._intent_distribution_chart(report))
        artifacts.append(self._objections_chart(report))
        artifacts.append(self._services_chart(report))
        artifacts.append(self._followup_returns_chart(bundle, history_start, day_end))
        artifacts.append(self._activity_heatmap(bundle, history_start, day_end))
        artifacts.append(self._dropoff_chart(report))

        return [chart for chart in artifacts if chart.file_path]

    def _save_current_figure(self, chart_name: str) -> ChartArtifact:
        path = self.output_dir / f"{chart_name}.png"
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()
        return ChartArtifact(chart_name=chart_name, file_path=str(path.resolve()))

    @staticmethod
    def _plot_empty_state(title: str) -> None:
        plt.figure(figsize=(8, 4))
        plt.text(0.5, 0.5, "No data", fontsize=14, ha="center", va="center")
        plt.title(title)
        plt.axis("off")

    def _funnel_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.funnel.leads_by_stage
        if not data:
            self._plot_empty_state("Funnel by Stage")
            return self._save_current_figure("funnel_stages")

        order = sorted(data.items(), key=lambda x: x[1], reverse=True)
        labels, values = zip(*order, strict=False)
        plt.figure(figsize=(9, 5))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="Blues_d",
            legend=False,
        )
        plt.title("Sales Funnel by Stage")
        plt.xlabel("Stage")
        plt.ylabel("Leads")
        plt.xticks(rotation=20)
        return self._save_current_figure("funnel_stages")

    def _stage_distribution_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.funnel.leads_by_stage
        if not data:
            self._plot_empty_state("Stage Distribution")
            return self._save_current_figure("stage_distribution")

        plt.figure(figsize=(7, 7))
        plt.pie(data.values(), labels=data.keys(), autopct="%1.1f%%", startangle=140)
        plt.title("Lead Distribution by Stage")
        return self._save_current_figure("stage_distribution")

    def _leads_trend_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        rows = [lead.created_at for lead in bundle.leads if lead.created_at and history_start <= lead.created_at < day_end]

        if not rows:
            self._plot_empty_state("New Leads Trend")
            return self._save_current_figure("new_leads_trend")

        df = pd.DataFrame({"created_at": pd.to_datetime(rows)})
        df["date"] = df["created_at"].dt.date
        series = df.groupby("date").size().sort_index()

        plt.figure(figsize=(10, 4))
        plt.plot(series.index, series.values, marker="o", color="#2563eb")
        plt.title("New Leads by Day")
        plt.xlabel("Date")
        plt.ylabel("Leads")
        plt.xticks(rotation=20)
        return self._save_current_figure("new_leads_trend")

    def _conversion_trend_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        lead_dates = [lead.created_at.date() for lead in bundle.leads if lead.created_at and history_start <= lead.created_at < day_end]
        booking_dates = [
            booking.created_at.date()
            for booking in bundle.bookings
            if history_start <= booking.created_at < day_end and (booking.status or "confirmed").lower() != "cancelled"
        ]

        if not lead_dates:
            self._plot_empty_state("Daily Conversion Trend")
            return self._save_current_figure("conversion_trend")

        lead_counter = Counter(lead_dates)
        booking_counter = Counter(booking_dates)
        all_days = sorted(lead_counter.keys())

        rates = []
        for day in all_days:
            leads = lead_counter.get(day, 0)
            bookings = booking_counter.get(day, 0)
            rate = (bookings / leads) * 100 if leads else 0
            rates.append(round(rate, 2))

        plt.figure(figsize=(10, 4))
        plt.plot(all_days, rates, marker="o", color="#0ea5e9")
        plt.title("Daily Conversion Rate (Booking / New Leads)")
        plt.xlabel("Date")
        plt.ylabel("Conversion %")
        plt.xticks(rotation=20)
        return self._save_current_figure("conversion_trend")

    def _intent_distribution_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.intents.intent_distribution
        if not data:
            self._plot_empty_state("Intent Distribution")
            return self._save_current_figure("intent_distribution")

        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        labels, values = zip(*sorted_items, strict=False)
        plt.figure(figsize=(10, 4))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="viridis",
            legend=False,
        )
        plt.title("Intent Distribution")
        plt.xlabel("Intent")
        plt.ylabel("Count")
        plt.xticks(rotation=20)
        return self._save_current_figure("intent_distribution")

    def _objections_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.intents.top_objection_categories
        if not data:
            self._plot_empty_state("Top Objections")
            return self._save_current_figure("top_objections")

        labels, values = zip(*data.items(), strict=False)
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="Reds",
            legend=False,
        )
        plt.title("Top Objection Categories")
        plt.xlabel("Category")
        plt.ylabel("Count")
        plt.xticks(rotation=20)
        return self._save_current_figure("top_objections")

    def _services_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.intents.top_services
        if not data:
            self._plot_empty_state("Top Services / Interests")
            return self._save_current_figure("top_services")

        labels, values = zip(*data.items(), strict=False)
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="mako",
            legend=False,
        )
        plt.title("Top Services / Interests")
        plt.xlabel("Service / Topic")
        plt.ylabel("Mentions")
        plt.xticks(rotation=20)
        return self._save_current_figure("top_services")

    def _followup_returns_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        rows = [
            fu.response_at.date()
            for fu in bundle.followups
            if fu.response_at and history_start <= fu.response_at < day_end
        ]

        if not rows:
            self._plot_empty_state("Returns After Follow-Up")
            return self._save_current_figure("followup_returns")

        counts = Counter(rows)
        days = sorted(counts.keys())
        values = [counts[day] for day in days]

        plt.figure(figsize=(10, 4))
        plt.bar(days, values, color="#22c55e")
        plt.title("Follow-Up Returns by Day")
        plt.xlabel("Date")
        plt.ylabel("Returned Leads")
        plt.xticks(rotation=20)
        return self._save_current_figure("followup_returns")

    def _activity_heatmap(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        points = [
            msg.created_at
            for msg in bundle.messages
            if history_start <= msg.created_at < day_end
        ]

        if not points:
            self._plot_empty_state("Dialog Activity Heatmap")
            return self._save_current_figure("activity_heatmap")

        df = pd.DataFrame({"created_at": pd.to_datetime(points)})
        df["weekday"] = df["created_at"].dt.day_name()
        df["hour"] = df["created_at"].dt.hour

        table = pd.pivot_table(
            df,
            index="weekday",
            columns="hour",
            values="created_at",
            aggfunc="count",
            fill_value=0,
        )

        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        table = table.reindex(weekday_order, fill_value=0)

        plt.figure(figsize=(12, 4))
        sns.heatmap(table, cmap="YlGnBu", linewidths=0.5)
        plt.title("Dialog Activity by Weekday and Hour")
        plt.xlabel("Hour")
        plt.ylabel("Weekday")
        return self._save_current_figure("activity_heatmap")

    def _dropoff_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        data = report.funnel.dropoff_points
        if not data:
            self._plot_empty_state("Drop-Off Points")
            return self._save_current_figure("dropoff_points")

        labels, values = zip(*sorted(data.items(), key=lambda x: x[1], reverse=True), strict=False)
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="rocket",
            legend=False,
        )
        plt.title("Lead Drop-Off by Stage")
        plt.xlabel("Stage")
        plt.ylabel("Lost Leads")
        plt.xticks(rotation=20)
        return self._save_current_figure("dropoff_points")
