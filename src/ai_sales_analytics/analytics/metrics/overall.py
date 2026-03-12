from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ai_sales_analytics.analytics.models import OverallMetrics
from ai_sales_analytics.analytics.rules import (
    is_inbound,
    is_outbound,
    meaningful_conversation,
    normalize_intent,
)
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    FollowUpRecord,
    LeadRecord,
    MessageRecord,
)


class OverallMetricsService:
    def calculate(
        self,
        leads: list[LeadRecord],
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        bookings: list[BookingRecord],
        followups: list[FollowUpRecord],
        day_end: datetime,
    ) -> OverallMetrics:
        all_leads = [lead for lead in leads if (lead.created_at is None or lead.created_at < day_end)]
        all_messages = [msg for msg in messages if msg.created_at < day_end]
        all_runs = [run for run in ai_runs if run.created_at < day_end]
        all_bookings = [
            booking
            for booking in bookings
            if booking.created_at < day_end and (booking.status or "confirmed").lower() != "cancelled"
        ]

        lead_ids_with_dialog = {msg.lead_id for msg in all_messages}

        incoming_count = sum(1 for msg in all_messages if is_inbound(msg))
        outgoing_count = sum(1 for msg in all_messages if is_outbound(msg))

        messages_by_lead: dict[str, list[MessageRecord]] = defaultdict(list)
        for msg in all_messages:
            messages_by_lead[msg.lead_id].append(msg)
        for items in messages_by_lead.values():
            items.sort(key=lambda x: x.created_at)

        meaningful_dialogs = sum(1 for items in messages_by_lead.values() if meaningful_conversation(items))

        target_action_from_bookings = {booking.lead_id for booking in all_bookings}
        target_action_from_leads = {
            lead.lead_id
            for lead in all_leads
            if (
                (lead.target_action_at is not None and lead.target_action_at < day_end)
                or (lead.stage or "").strip().lower() == "booked"
            )
        }
        target_action_leads = target_action_from_bookings | target_action_from_leads

        lost_leads = {
            lead.lead_id
            for lead in all_leads
            if (lead.status or "").lower() in {"lost", "closed_lost"}
            or (lead.stage or "").strip().lower() == "lost"
        }

        handoff_from_messages = {
            msg.lead_id
            for msg in all_messages
            if normalize_intent(msg.intent, msg.text) == "human_handoff"
        }
        handoff_from_runs = {run.lead_id for run in all_runs if run.handoff_to_human}
        handoff_leads = handoff_from_messages | handoff_from_runs

        followup_returns = 0
        for followup in followups:
            if followup.sent_at >= day_end:
                continue
            if followup.response_at and followup.response_at < day_end:
                followup_returns += 1

        conversion_numerator = len(target_action_leads & lead_ids_with_dialog)
        conversion_denominator = len(lead_ids_with_dialog)
        conversion_rate = (
            round((conversion_numerator / conversion_denominator) * 100, 2)
            if conversion_denominator
            else 0.0
        )

        avg_messages_per_dialog = (
            round(len(all_messages) / conversion_denominator, 2) if conversion_denominator else 0.0
        )

        period_start_candidates = [
            *(lead.created_at for lead in all_leads if lead.created_at is not None),
            *(msg.created_at for msg in all_messages),
        ]
        period_start = min(period_start_candidates).isoformat() if period_start_candidates else None

        return OverallMetrics(
            period_start=period_start,
            period_end=day_end.isoformat(),
            total_leads=len(all_leads),
            total_dialogs=conversion_denominator,
            total_incoming_messages=incoming_count,
            total_outgoing_messages=outgoing_count,
            total_meaningful_dialogs=meaningful_dialogs,
            total_target_actions=len(target_action_leads),
            total_lost_leads=len(lost_leads),
            total_handoff_to_human=len(handoff_leads),
            total_followup_returns=followup_returns,
            overall_conversion_rate=conversion_rate,
            conversion_numerator=conversion_numerator,
            conversion_denominator=conversion_denominator,
            conversion_formula="конверсия = лиды с целевым действием / лиды с диалогом * 100%",
            avg_messages_per_dialog=avg_messages_per_dialog,
        )
