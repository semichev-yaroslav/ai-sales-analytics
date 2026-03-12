from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ai_sales_analytics.analytics.models import ChartArtifact, DailyAnalyticsReport
from ai_sales_analytics.db.contracts import DataBundle
from ai_sales_analytics.localization import (
    intent_label,
    objection_category_label,
    stage_label,
    weekday_label,
)

matplotlib.use("Agg")

logger = logging.getLogger(__name__)
sns.set_theme(style="whitegrid")

WEEKDAY_ORDER_EN = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
WEEKDAY_ORDER_RU = [weekday_label(day) for day in WEEKDAY_ORDER_EN]


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

    def _save_current_figure(self, file_stem: str, chart_name: str) -> ChartArtifact:
        path = self.output_dir / f"{file_stem}.png"
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()
        return ChartArtifact(chart_name=chart_name, file_path=str(path.resolve()))

    @staticmethod
    def _plot_empty_state(title: str) -> None:
        plt.figure(figsize=(8, 4))
        plt.text(0.5, 0.5, "Нет данных", fontsize=14, ha="center", va="center")
        plt.title(title)
        plt.axis("off")

    def _funnel_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Воронка продаж по стадиям"
        data = report.funnel.leads_by_stage
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("funnel_stages", chart_name)

        order = sorted(data.items(), key=lambda x: x[1], reverse=True)
        labels, values = zip(*order, strict=False)
        labels_ru = [stage_label(item) for item in labels]
        plt.figure(figsize=(9, 5))
        sns.barplot(
            x=list(labels_ru),
            y=list(values),
            hue=list(labels_ru),
            palette="Blues_d",
            legend=False,
        )
        plt.title(chart_name)
        plt.xlabel("Стадия")
        plt.ylabel("Количество лидов")
        plt.xticks(rotation=20)
        return self._save_current_figure("funnel_stages", chart_name)

    def _stage_distribution_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Распределение лидов по стадиям"
        data = report.funnel.leads_by_stage
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("stage_distribution", chart_name)

        labels_ru = [stage_label(stage) for stage in data.keys()]
        plt.figure(figsize=(7, 7))
        plt.pie(data.values(), labels=labels_ru, autopct="%1.1f%%", startangle=140)
        plt.title(chart_name)
        return self._save_current_figure("stage_distribution", chart_name)

    def _leads_trend_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        chart_name = "Динамика новых лидов"
        rows = [
            lead.created_at
            for lead in bundle.leads
            if lead.created_at and history_start <= lead.created_at < day_end
        ]

        if not rows:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("new_leads_trend", chart_name)

        df = pd.DataFrame({"created_at": pd.to_datetime(rows)})
        df["date"] = df["created_at"].dt.date
        series = df.groupby("date").size().sort_index()

        plt.figure(figsize=(10, 4))
        plt.plot(series.index, series.values, marker="o", color="#2563eb")
        plt.title(chart_name)
        plt.xlabel("Дата")
        plt.ylabel("Количество лидов")
        plt.xticks(rotation=20)
        return self._save_current_figure("new_leads_trend", chart_name)

    def _conversion_trend_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        chart_name = "Динамика конверсии"
        lead_dates = [
            lead.created_at.date()
            for lead in bundle.leads
            if lead.created_at and history_start <= lead.created_at < day_end
        ]
        booking_dates = [
            booking.created_at.date()
            for booking in bundle.bookings
            if history_start <= booking.created_at < day_end
            and (booking.status or "confirmed").lower() != "cancelled"
        ]

        if not lead_dates:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("conversion_trend", chart_name)

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
        plt.title(chart_name)
        plt.xlabel("Дата")
        plt.ylabel("Конверсия, %")
        plt.xticks(rotation=20)
        return self._save_current_figure("conversion_trend", chart_name)

    def _intent_distribution_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Распределение интентов"
        data = report.intents.intent_distribution
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("intent_distribution", chart_name)

        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        labels, values = zip(*sorted_items, strict=False)
        labels_ru = [intent_label(item) for item in labels]
        plt.figure(figsize=(10, 4))
        sns.barplot(
            x=list(labels_ru),
            y=list(values),
            hue=list(labels_ru),
            palette="viridis",
            legend=False,
        )
        plt.title(chart_name)
        plt.xlabel("Интент")
        plt.ylabel("Количество")
        plt.xticks(rotation=20)
        return self._save_current_figure("intent_distribution", chart_name)

    def _objections_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Топ категорий возражений"
        data = report.intents.top_objection_categories
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("top_objections", chart_name)

        labels, values = zip(*data.items(), strict=False)
        labels_ru = [objection_category_label(item) for item in labels]
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels_ru),
            y=list(values),
            hue=list(labels_ru),
            palette="Reds",
            legend=False,
        )
        plt.title(chart_name)
        plt.xlabel("Категория")
        plt.ylabel("Количество")
        plt.xticks(rotation=20)
        return self._save_current_figure("top_objections", chart_name)

    def _services_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Топ услуг и тем интереса"
        data = report.intents.top_services
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("top_services", chart_name)

        labels, values = zip(*data.items(), strict=False)
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels),
            y=list(values),
            hue=list(labels),
            palette="mako",
            legend=False,
        )
        plt.title(chart_name)
        plt.xlabel("Услуга / тема")
        plt.ylabel("Упоминаний")
        plt.xticks(rotation=20)
        return self._save_current_figure("top_services", chart_name)

    def _followup_returns_chart(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        chart_name = "Возвраты после повторного контакта"
        rows = [
            fu.response_at.date()
            for fu in bundle.followups
            if fu.response_at and history_start <= fu.response_at < day_end
        ]

        if not rows:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("followup_returns", chart_name)

        counts = Counter(rows)
        days = sorted(counts.keys())
        values = [counts[day] for day in days]

        plt.figure(figsize=(10, 4))
        plt.bar(days, values, color="#22c55e")
        plt.title(chart_name)
        plt.xlabel("Дата")
        plt.ylabel("Количество возвратов")
        plt.xticks(rotation=20)
        return self._save_current_figure("followup_returns", chart_name)

    def _activity_heatmap(self, bundle: DataBundle, history_start: datetime, day_end: datetime) -> ChartArtifact:
        chart_name = "Тепловая карта активности диалогов"
        points = [
            msg.created_at
            for msg in bundle.messages
            if history_start <= msg.created_at < day_end
        ]

        if not points:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("activity_heatmap", chart_name)

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

        table.index = [weekday_label(day) for day in table.index]
        table = table.reindex(WEEKDAY_ORDER_RU, fill_value=0)

        plt.figure(figsize=(12, 4))
        sns.heatmap(table, cmap="YlGnBu", linewidths=0.5)
        plt.title(chart_name)
        plt.xlabel("Час")
        plt.ylabel("День недели")
        return self._save_current_figure("activity_heatmap", chart_name)

    def _dropoff_chart(self, report: DailyAnalyticsReport) -> ChartArtifact:
        chart_name = "Точки потери лидов по стадиям"
        data = report.funnel.dropoff_points
        if not data:
            self._plot_empty_state(chart_name)
            return self._save_current_figure("dropoff_points", chart_name)

        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        labels, values = zip(*sorted_items, strict=False)
        labels_ru = [stage_label(item) for item in labels]
        plt.figure(figsize=(9, 4))
        sns.barplot(
            x=list(labels_ru),
            y=list(values),
            hue=list(labels_ru),
            palette="rocket",
            legend=False,
        )
        plt.title(chart_name)
        plt.xlabel("Стадия")
        plt.ylabel("Потерянные лиды")
        plt.xticks(rotation=20)
        return self._save_current_figure("dropoff_points", chart_name)
