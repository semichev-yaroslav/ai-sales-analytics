from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from ai_sales_analytics.db.contracts import MessageRecord

DEFAULT_STAGE_ORDER = [
    "new",
    "qualified",
    "interested",
    "objection",
    "booking_pending",
    "booked",
    "lost",
]

QUESTION_PATTERNS = {
    "price": [r"\bprice\b", r"\bcost\b", r"\bhow much\b", r"\bцена\b", r"\bстоим"],
    "timeline": [r"\bwhen\b", r"\bhow long\b", r"\bсрок\b", r"\bкогда\b"],
    "service_scope": [r"\bwhat include\b", r"\bчто входит\b", r"\bуслуг"],
    "guarantee": [r"\bguarante\b", r"\bгарант"],
}

OBJECTION_PATTERNS = {
    "too_expensive": [r"expensive", r"дорого", r"слишком дорого"],
    "need_time": [r"need to think", r"подумаю", r"не сейчас"],
    "no_trust": [r"not sure", r"сомнева", r"отзывы", r"кейсы"],
    "competitor": [r"other company", r"у других", r"конкурент"],
}

INTENT_KEYWORDS = {
    "price_question": [r"price", r"cost", r"цена", r"стоим"],
    "objection": [r"дорого", r"expensive", r"сомнева", r"не уверен", r"подума"],
    "booking_intent": [r"book", r"appointment", r"консультац", r"запис"],
    "contact_sharing": [r"@", r"\+\d{9,}", r"telegram", r"whatsapp", r"email"],
    "human_handoff": [r"manager", r"human", r"человек", r"оператор", r"менеджер"],
}

UNCLEAR_INTENTS = {"unknown", "unclear", "low_confidence", "fallback", "none"}


@dataclass(slots=True)
class ConversationStats:
    inbound_count: int
    outbound_count: int
    total_count: int



def _text_matches_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)



def infer_intent_from_text(text: str | None) -> str:
    if not text:
        return "unknown"

    for intent, patterns in INTENT_KEYWORDS.items():
        if _text_matches_any(text, patterns):
            return intent
    return "general_question"



def normalize_intent(intent: str | None, text: str | None) -> str:
    if intent and intent.strip():
        normalized = intent.strip().lower().replace(" ", "_")
        if normalized in UNCLEAR_INTENTS:
            return "unclear"
        return normalized
    return infer_intent_from_text(text)



def is_inbound(message: MessageRecord) -> bool:
    direction = (message.direction or "").lower()
    role = (message.role or "").lower()
    if direction in {"in", "inbound", "incoming", "user"}:
        return True
    if direction in {"out", "outbound", "bot", "assistant", "ai"}:
        return False
    return role in {"user", "client", "human"}



def is_outbound(message: MessageRecord) -> bool:
    return not is_inbound(message)



def meaningful_conversation(messages: list[MessageRecord]) -> bool:
    inbound = sum(1 for msg in messages if is_inbound(msg))
    outbound = sum(1 for msg in messages if is_outbound(msg))
    return inbound >= 2 and outbound >= 1



def extract_question_category(text: str | None) -> str | None:
    if not text:
        return None
    for category, patterns in QUESTION_PATTERNS.items():
        if _text_matches_any(text, patterns):
            return category
    if text.strip().endswith("?"):
        return "general"
    return None



def extract_objection_category(text: str | None) -> str | None:
    if not text:
        return None
    for category, patterns in OBJECTION_PATTERNS.items():
        if _text_matches_any(text, patterns):
            return category
    return None



def top_n(counter: Counter[str], n: int = 8) -> dict[str, int]:
    return {key: value for key, value in counter.most_common(n)}
