from __future__ import annotations

from ai_sales_analytics.analytics.models import (
    DailyKPI,
    FunnelMetrics,
    InsightBlock,
    IntentMetrics,
    QualityMetrics,
)
from ai_sales_analytics.localization import (
    objection_category_label,
    replace_risk_terms,
    stage_label,
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
                "Пересобрать сценарий перехода из статуса 'Заинтересован' в статус "
                "'Ожидает записи': добавить явный призыв к действию и оффер на консультацию."
            )

        if funnel.dropoff_points:
            stage, count = max(funnel.dropoff_points.items(), key=lambda x: x[1])
            readable_stage = stage_label(stage)
            findings.append(f"Основной отвал происходит на стадии '{readable_stage}' ({count} лидов).")
            recommendations.append(
                f"Проверить шаблоны ответов на стадии '{readable_stage}' и добавить "
                "ответы на частые возражения до запроса контакта."
            )

        if intents.top_objection_categories:
            top_obj, obj_count = max(intents.top_objection_categories.items(), key=lambda x: x[1])
            readable_obj = objection_category_label(top_obj)
            findings.append(f"Топ-возражение дня: '{readable_obj}' ({obj_count} упоминаний).")
            recommendations.append(
                f"Добавить в скрипт бота отдельный обработчик возражений для категории '{readable_obj}'."
            )

        if quality.low_confidence_rate > 18:
            risks.append(
                f"Высокая доля кейсов низкой уверенности модели и нераспознанных запросов: "
                f"{quality.low_confidence_rate:.1f}%."
            )
            recommendations.append(
                "Уточнить таксономию интентов и добавить примеры запросов для нераспознанных случаев."
            )

        if quality.no_meaningful_progress_rate > 45:
            risks.append(
                f"Много диалогов без заметного прогресса: {quality.no_meaningful_progress_rate:.1f}%."
            )
            recommendations.append(
                "Сократить путь до следующего шага: предлагать 2 готовых временных слота "
                "уже во 2-3 сообщении."
            )

        if kpi.handoff_to_human > 0 and quality.handoff_rate > 20:
            risks.append("Заметная зависимость от передачи диалога менеджеру.")
            recommendations.append(
                "Проанализировать диалоги с передачей менеджеру и закрыть пробелы в скрипте "
                "бота по этим сценариям."
            )

        if intents.top_services:
            top_service, service_count = max(intents.top_services.items(), key=lambda x: x[1])
            findings.append(f"Наибольший интерес к услуге/теме '{top_service}' ({service_count} упоминаний).")
            recommendations.append(
                f"Вынести '{top_service}' в более ранний блок диалога и подготовить "
                "короткое ценностное предложение."
            )

        if not findings:
            findings.append("Критических просадок по воронке за период не выявлено.")

        if not recommendations:
            recommendations.append(
                "Поддерживать текущий сценарий и провести A/B тест первого сообщения "
                "для роста конверсии."
            )

        findings = [replace_risk_terms(item) for item in findings]
        recommendations = [replace_risk_terms(item) for item in recommendations]
        risks = [replace_risk_terms(item) for item in risks]

        return InsightBlock(
            key_findings=findings[:6],
            recommendations=recommendations[:8],
            risk_flags=risks[:5],
        )
