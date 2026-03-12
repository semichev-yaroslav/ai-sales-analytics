from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from ai_sales_analytics.analytics.models import IntentMetrics
from ai_sales_analytics.analytics.rules import (
    extract_objection_category,
    extract_question_category,
    is_inbound,
    normalize_intent,
    top_n,
)
from ai_sales_analytics.analytics.utils import in_window
from ai_sales_analytics.db.contracts import AIRunRecord, BookingRecord, LeadRecord, MessageRecord


class IntentAnalyticsService:
    def __init__(self, low_confidence_threshold: float, lost_lead_inactivity_hours: int):
        self.low_confidence_threshold = low_confidence_threshold
        self.lost_lead_inactivity_hours = lost_lead_inactivity_hours

    def calculate(
        self,
        leads: list[LeadRecord],
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        bookings: list[BookingRecord],
        day_start: datetime,
        day_end: datetime,
    ) -> IntentMetrics:
        day_messages = [msg for msg in messages if in_window(msg.created_at, day_start, day_end) and is_inbound(msg)]
        day_runs = [run for run in ai_runs if in_window(run.created_at, day_start, day_end)]

        intent_counter: Counter[str] = Counter()
        question_counter: Counter[str] = Counter()
        objection_counter: Counter[str] = Counter()
        services_counter: Counter[str] = Counter()

        price_questions = 0
        objections = 0
        unclear = 0
        booking_intents = 0
        contact_sharing = 0
        human_handoff_dialogs = set()

        for msg in day_messages:
            intent = normalize_intent(msg.intent, msg.text)
            intent_counter[intent] += 1

            if intent == "price_question":
                price_questions += 1
            elif intent == "objection":
                objections += 1
            elif intent == "booking_intent":
                booking_intents += 1
            elif intent == "contact_sharing":
                contact_sharing += 1
            elif intent == "human_handoff":
                human_handoff_dialogs.add(msg.lead_id)

            if intent == "unclear" or (msg.confidence is not None and msg.confidence < self.low_confidence_threshold):
                unclear += 1

            question_category = extract_question_category(msg.text)
            if question_category:
                question_counter[question_category] += 1

            objection_category = extract_objection_category(msg.text)
            if objection_category:
                objection_counter[objection_category] += 1

            if msg.service_topic:
                services_counter[msg.service_topic.strip().lower()] += 1

        for run in day_runs:
            if (run.confidence is not None and run.confidence < self.low_confidence_threshold) or (
                normalize_intent(run.intent, None) == "unclear"
            ):
                unclear += 1
            if run.handoff_to_human:
                human_handoff_dialogs.add(run.lead_id)

        for booking in bookings:
            if in_window(booking.created_at, day_start, day_end) and booking.service_name:
                services_counter[booking.service_name.strip().lower()] += 1

        loss_reasons = Counter()
        for lead in leads:
            if (lead.status or "").lower() in {"lost", "closed_lost"} and lead.lost_reason:
                loss_reasons[lead.lost_reason.strip().lower()] += 1

        messages_by_lead = defaultdict(list)
        for msg in messages:
            if msg.created_at < day_end:
                messages_by_lead[msg.lead_id].append(msg)
        for msg_list in messages_by_lead.values():
            msg_list.sort(key=lambda m: m.created_at)

        inactivity_cutoff = day_end - timedelta(hours=self.lost_lead_inactivity_hours)
        ghosted = 0
        for msg_list in messages_by_lead.values():
            if not msg_list:
                continue
            latest = msg_list[-1]
            if latest.created_at <= inactivity_cutoff and not is_inbound(latest):
                ghosted += 1

        return IntentMetrics(
            intent_distribution=dict(intent_counter),
            top_question_categories=top_n(question_counter, n=8),
            top_objection_categories=top_n(objection_counter, n=8),
            top_services=top_n(services_counter, n=8),
            price_questions=price_questions,
            objections=objections,
            unclear_cases=unclear,
            booking_intents=booking_intents,
            contact_sharing_intents=contact_sharing,
            ghosted_leads=ghosted,
            human_handoff_dialogs=len(human_handoff_dialogs),
            loss_reasons=dict(loss_reasons),
        )
