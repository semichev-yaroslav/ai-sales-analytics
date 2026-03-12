from __future__ import annotations

from ai_sales_analytics.analytics.models import DailyAnalyticsReport
from ai_sales_analytics.localization import stage_label


def build_telegram_summary(report: DailyAnalyticsReport) -> str:
    findings = "\n".join([f"- {item}" for item in report.insights.key_findings[:3]])
    recommendations = "\n".join([f"- {item}" for item in report.insights.recommendations[:3]])
    top_dropoff = (
        max(report.funnel.dropoff_points, key=report.funnel.dropoff_points.get)
        if report.funnel.dropoff_points
        else None
    )

    return (
        f"Ежедневная сводка по AI-продажам ({report.report_date})\n"
        f"\n"
        f"Общая результативность (за все время):\n"
        f"• Лидов всего: {report.overall.total_leads}\n"
        f"• Целевых действий всего: {report.overall.total_target_actions}\n"
        f"• Конверсия за все время: {report.overall.overall_conversion_rate}% "
        f"({report.overall.conversion_numerator}/{report.overall.conversion_denominator})\n"
        f"\n"
        f"Ключевые показатели:\n"
        f"• Новые лиды: {report.kpi.new_leads}\n"
        f"• Активные диалоги: {report.kpi.active_dialogs}\n"
        f"• Целевые действия: {report.kpi.target_actions}\n"
        f"• Потерянные лиды: {report.kpi.lost_leads}\n"
        f"• Передачи менеджеру: {report.kpi.handoff_to_human}\n"
        f"• Диалоги для ручной проверки: {report.dialog_review.risky_dialogs}\n"
        f"\n"
        f"Воронка:\n"
        f"• Общая конверсия: {report.funnel.overall_conversion_rate}%\n"
        f"• Как считали: {report.funnel.conversion_target_actions} / "
        f"{report.funnel.conversion_conversational_leads} лидов с диалогом\n"
        f"• Главная точка отвала: {stage_label(top_dropoff) if top_dropoff else 'нет данных'}\n"
        f"\n"
        f"Ключевые выводы:\n{findings if findings else '- Явных аномалий не выявлено'}\n"
        f"\n"
        f"Рекомендации:\n{recommendations if recommendations else '- Поддерживать текущий сценарий'}"
    )
