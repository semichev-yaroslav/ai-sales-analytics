from __future__ import annotations

from collections.abc import Mapping

STAGE_LABELS_RU: dict[str, str] = {
    "new": "Новый лид",
    "engaged": "В диалоге",
    "qualified": "Квалифицирован",
    "interested": "Заинтересован",
    "objection": "Есть возражение",
    "booking_pending": "Ожидает записи",
    "booked": "Записан",
    "lost": "Потерян",
    "unknown": "Не определено",
}

INTENT_LABELS_RU: dict[str, str] = {
    "greeting": "Приветствие",
    "service_question": "Вопрос по услуге",
    "general_question": "Общий вопрос",
    "price_question": "Вопрос о цене",
    "objection": "Возражение",
    "ready_to_buy": "Готов к покупке",
    "booking_intent": "Намерение записаться",
    "contact_sharing": "Передача контактов",
    "human_handoff": "Запрос менеджера",
    "unclear": "Нераспознанный запрос",
    "unknown": "Неизвестно",
}

QUESTION_CATEGORY_LABELS_RU: dict[str, str] = {
    "price": "Цена",
    "timeline": "Сроки",
    "service_scope": "Состав услуги",
    "guarantee": "Гарантии",
    "general": "Общий вопрос",
}

OBJECTION_CATEGORY_LABELS_RU: dict[str, str] = {
    "too_expensive": "Дорого",
    "need_time": "Нужно подумать",
    "no_trust": "Недостаток доверия",
    "competitor": "Сравнение с конкурентами",
}

RISK_TERMS_RU: dict[str, str] = {
    "low-confidence": "низкой уверенности модели",
    "unclear": "нераспознанных запросов",
    "meaningful progress": "заметного прогресса",
    "handoff": "передачи менеджеру",
    "intent taxonomy": "таксономию интентов",
    "value proposition": "ценностное предложение",
}

WEEKDAY_LABELS_RU: dict[str, str] = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье",
}


def _clean_key(value: str | None) -> str:
    if not value:
        return "unknown"
    return value.strip().lower().replace(" ", "_")


def _fallback_humanized(value: str | None) -> str:
    if not value:
        return "Не указано"
    return value.replace("_", " ").strip()


def _translate(value: str | None, mapping: Mapping[str, str]) -> str:
    key = _clean_key(value)
    if key in mapping:
        return mapping[key]
    return _fallback_humanized(value)


def stage_label(value: str | None) -> str:
    return _translate(value, STAGE_LABELS_RU)


def intent_label(value: str | None) -> str:
    return _translate(value, INTENT_LABELS_RU)


def question_category_label(value: str | None) -> str:
    return _translate(value, QUESTION_CATEGORY_LABELS_RU)


def objection_category_label(value: str | None) -> str:
    return _translate(value, OBJECTION_CATEGORY_LABELS_RU)


def generic_label(value: str | None) -> str:
    return _fallback_humanized(value)


def weekday_label(value: str) -> str:
    return WEEKDAY_LABELS_RU.get(value, value)


def stage_transition_label(value: str) -> str:
    parts = value.split("->")
    if len(parts) != 2:
        return generic_label(value)
    src, dst = parts
    return f"{stage_label(src)} -> {stage_label(dst)}"


def replace_risk_terms(text: str) -> str:
    normalized = text
    for source, target in RISK_TERMS_RU.items():
        normalized = normalized.replace(source, target)
    return normalized
