from __future__ import annotations

from ai_sales_analytics.analytics.models import DailyAnalyticsReport


def build_telegram_summary(report: DailyAnalyticsReport) -> str:
    findings = "\n".join([f"- {item}" for item in report.insights.key_findings[:3]])
    recommendations = "\n".join([f"- {item}" for item in report.insights.recommendations[:3]])

    return (
        f"AI Sales Daily Summary ({report.report_date})\n"
        f"\n"
        f"KPI:\n"
        f"• New leads: {report.kpi.new_leads}\n"
        f"• Active dialogs: {report.kpi.active_dialogs}\n"
        f"• Target actions: {report.kpi.target_actions}\n"
        f"• Lost leads: {report.kpi.lost_leads}\n"
        f"• Handoff: {report.kpi.handoff_to_human}\n"
        f"\n"
        f"Funnel:\n"
        f"• Overall conversion: {report.funnel.overall_conversion_rate}%\n"
        f"• Top drop-off: {max(report.funnel.dropoff_points, key=report.funnel.dropoff_points.get) if report.funnel.dropoff_points else 'n/a'}\n"
        f"\n"
        f"Main findings:\n{findings if findings else '- Нет явных аномалий'}\n"
        f"\n"
        f"Recommendations:\n{recommendations if recommendations else '- Поддерживать текущий сценарий'}"
    )
