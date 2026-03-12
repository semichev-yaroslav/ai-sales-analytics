from __future__ import annotations

from ai_sales_analytics.analytics.models import (
    DailyKPI,
    FunnelMetrics,
    InsightBlock,
    IntentMetrics,
    QualityMetrics,
)


class HeuristicInsightEngine:
    def generate(
        self,
        kpi: DailyKPI,
        funnel: FunnelMetrics,
        intents: IntentMetrics,
        quality: QualityMetrics,
    ) -> InsightBlock:
        findings: list[str] = []
        recommendations: list[str] = []
        risks: list[str] = []

        if funnel.overall_conversion_rate < 15:
            findings.append(
                f"Низкая общая конверсия в целевое действие: {funnel.overall_conversion_rate:.1f}%"
            )
            recommendations.append(
                "Пересобрать сценарий перехода из 'interested' в 'booking_pending': добавить явный CTA и оффер на консультацию."
            )

        if funnel.dropoff_points:
            stage, count = max(funnel.dropoff_points.items(), key=lambda x: x[1])
            findings.append(f"Основной отвал происходит на стадии '{stage}' ({count} лидов).")
            recommendations.append(
                f"Проверить шаблоны ответов на стадии '{stage}' и добавить ответ на частые возражения до запроса контакта."
            )

        if intents.top_objection_categories:
            top_obj, obj_count = max(intents.top_objection_categories.items(), key=lambda x: x[1])
            findings.append(f"Топ-возражение дня: '{top_obj}' ({obj_count} упоминаний).")
            recommendations.append(
                f"Добавить в скрипт бота отдельный objection-handler для категории '{top_obj}'."
            )

        if quality.low_confidence_rate > 18:
            risks.append(
                f"Высокая доля low-confidence/unclear кейсов: {quality.low_confidence_rate:.1f}%."
            )
            recommendations.append(
                "Уточнить intent taxonomy и добавить few-shot примеры для нераспознанных запросов."
            )

        if quality.no_meaningful_progress_rate > 45:
            risks.append(
                f"Много диалогов без meaningful progress: {quality.no_meaningful_progress_rate:.1f}%."
            )
            recommendations.append(
                "Сократить путь до следующего шага: предлагать 2 готовых временных слота уже во 2-3 сообщении."
            )

        if kpi.handoff_to_human > 0 and quality.handoff_rate > 20:
            risks.append("Заметная зависимость от handoff к менеджеру.")
            recommendations.append(
                "Проанализировать handoff диалоги и закрыть пробелы в скрипте бота по этим сценариям."
            )

        if intents.top_services:
            top_service, service_count = max(intents.top_services.items(), key=lambda x: x[1])
            findings.append(f"Наибольший интерес к услуге/теме '{top_service}' ({service_count} упоминаний).")
            recommendations.append(
                f"Вынести '{top_service}' в более ранний блок диалога и подготовить короткий value proposition."
            )

        if not findings:
            findings.append("Критических просадок по воронке за период не выявлено.")

        if not recommendations:
            recommendations.append("Поддерживать текущий сценарий и провести A/B тест первого сообщения для роста конверсии.")

        return InsightBlock(
            key_findings=findings[:6],
            recommendations=recommendations[:8],
            risk_flags=risks[:5],
        )
