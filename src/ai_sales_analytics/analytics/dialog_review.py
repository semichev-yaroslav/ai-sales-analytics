from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ai_sales_analytics.analytics.models import DialogMessage, DialogReviewBlock, DialogReviewItem
from ai_sales_analytics.analytics.rules import is_inbound, normalize_intent
from ai_sales_analytics.analytics.utils import in_window
from ai_sales_analytics.db.contracts import AIRunRecord, LeadRecord, MessageRecord


class DialogReviewService:
    def __init__(self, low_confidence_threshold: float):
        self.low_confidence_threshold = low_confidence_threshold

    def build_daily(
        self,
        leads: list[LeadRecord],
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        day_start: datetime,
        day_end: datetime,
        limit: int = 20,
    ) -> DialogReviewBlock:
        day_messages = [msg for msg in messages if in_window(msg.created_at, day_start, day_end)]
        day_runs = [run for run in ai_runs if in_window(run.created_at, day_start, day_end)]

        messages_by_lead: dict[str, list[MessageRecord]] = defaultdict(list)
        runs_by_lead: dict[str, list[AIRunRecord]] = defaultdict(list)
        leads_by_id = {lead.lead_id: lead for lead in leads}

        for msg in day_messages:
            messages_by_lead[msg.lead_id].append(msg)
        for run in day_runs:
            runs_by_lead[run.lead_id].append(run)

        for items in messages_by_lead.values():
            items.sort(key=lambda x: x.created_at)
        for items in runs_by_lead.values():
            items.sort(key=lambda x: x.created_at)

        review_items: list[DialogReviewItem] = []

        for lead_id, lead_messages in messages_by_lead.items():
            lead = leads_by_id.get(lead_id)
            item = self._build_lead_dialog_item(
                lead=lead,
                lead_id=lead_id,
                messages=lead_messages,
                ai_runs=runs_by_lead.get(lead_id, []),
            )
            review_items.append(item)

        review_items.sort(key=lambda x: (x.risk_score, x.last_activity_at), reverse=True)

        risky_count = sum(1 for item in review_items if item.risk_score >= 3)
        return DialogReviewBlock(
            total_dialogs=len(review_items),
            risky_dialogs=risky_count,
            items=review_items[:limit],
        )

    def _build_lead_dialog_item(
        self,
        lead: LeadRecord | None,
        lead_id: str,
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
    ) -> DialogReviewItem:
        transcripts: list[DialogMessage] = []

        intents_seen: set[str] = set()
        low_confidence_hits = 0
        handoff_detected = False

        inbound_runs = list(ai_runs)
        inbound_run_index = 0

        for message in messages:
            speaker = "Клиент" if is_inbound(message) else "Бот"
            run = None
            if is_inbound(message) and inbound_run_index < len(inbound_runs):
                run = inbound_runs[inbound_run_index]
                inbound_run_index += 1

            detected_intent = normalize_intent(
                message.intent if message.intent is not None else (run.intent if run else None),
                message.text,
            )
            confidence = message.confidence if message.confidence is not None else (run.confidence if run else None)

            if is_inbound(message):
                intents_seen.add(detected_intent)

            if confidence is not None and confidence < self.low_confidence_threshold:
                low_confidence_hits += 1

            if run and run.handoff_to_human:
                handoff_detected = True

            transcripts.append(
                DialogMessage(
                    timestamp=message.created_at.isoformat(),
                    speaker=speaker,
                    text=(message.text or "").strip(),
                    detected_intent=detected_intent if is_inbound(message) else None,
                    confidence=round(confidence, 2) if confidence is not None else None,
                )
            )

        risk_flags: list[str] = []
        risk_score = 0

        stage = (lead.stage.lower() if lead and lead.stage else "unknown")
        if stage == "lost":
            risk_flags.append("Лид потерян: стоит проверить причину и момент отвала")
            risk_score += 4

        if low_confidence_hits > 0:
            risk_flags.append("Есть сообщения с низкой уверенностью распознавания")
            risk_score += 2

        if "unclear" in intents_seen:
            risk_flags.append("В диалоге есть нераспознанные запросы")
            risk_score += 2

        next_step_intents = {"booking_intent", "contact_sharing", "human_handoff", "ready_to_buy"}
        if stage != "booked" and not (intents_seen & next_step_intents):
            risk_flags.append("Бот не довел клиента до следующего шага")
            risk_score += 2

        if handoff_detected:
            risk_flags.append("Потребовалась передача менеджеру")
            risk_score += 1

        if len(messages) <= 3:
            risk_flags.append("Короткий диалог: клиент мог уйти без проработки")
            risk_score += 1

        if not risk_flags:
            risk_flags.append("Диалог прошел без критических проблем")

        return DialogReviewItem(
            lead_id=lead_id,
            stage=stage,
            message_count=len(messages),
            started_at=messages[0].created_at.isoformat(),
            last_activity_at=messages[-1].created_at.isoformat(),
            risk_score=risk_score,
            risk_flags=risk_flags,
            transcript=transcripts,
        )
