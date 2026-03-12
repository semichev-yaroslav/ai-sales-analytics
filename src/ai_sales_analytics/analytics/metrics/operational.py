from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ai_sales_analytics.analytics.models import DailyKPI
from ai_sales_analytics.analytics.rules import (
    is_inbound,
    is_outbound,
    meaningful_conversation,
    normalize_intent,
)
from ai_sales_analytics.analytics.utils import group_messages_by_lead, in_window
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    FollowUpRecord,
    LeadRecord,
    MessageRecord,
    StageEventRecord,
)


class OperationalMetricsService:
    def calculate(
        self,
        leads: list[LeadRecord],
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        bookings: list[BookingRecord],
        followups: list[FollowUpRecord],
        stage_events: list[StageEventRecord],
        day_start: datetime,
        day_end: datetime,
    ) -> DailyKPI:
        day_messages = [msg for msg in messages if in_window(msg.created_at, day_start, day_end)]
        day_ai_runs = [run for run in ai_runs if in_window(run.created_at, day_start, day_end)]
        day_bookings = [booking for booking in bookings if in_window(booking.created_at, day_start, day_end)]
        day_followups = [fu for fu in followups if in_window(fu.sent_at, day_start, day_end)]

        active_dialogs = len({msg.lead_id for msg in day_messages})
        incoming = sum(1 for msg in day_messages if is_inbound(msg))
        outgoing = sum(1 for msg in day_messages if is_outbound(msg))

        new_leads = sum(1 for lead in leads if in_window(lead.created_at, day_start, day_end))

        messages_by_lead = group_messages_by_lead(messages)
        new_dialogs = 0
        meaningful = 0
        for _lead_id, lead_messages in messages_by_lead.items():
            first_message = lead_messages[0]
            if in_window(first_message.created_at, day_start, day_end):
                new_dialogs += 1

            daily_msgs = [msg for msg in lead_messages if in_window(msg.created_at, day_start, day_end)]
            if daily_msgs and meaningful_conversation(daily_msgs):
                meaningful += 1

        booking_leads = {b.lead_id for b in day_bookings if (b.status or "confirmed").lower() != "cancelled"}
        target_action_leads = set(booking_leads)
        target_action_leads.update(
            {
                lead.lead_id
                for lead in leads
                if lead.target_action_at is not None and in_window(lead.target_action_at, day_start, day_end)
            }
        )

        lost_leads = {
            lead.lead_id
            for lead in leads
            if (lead.status or "").lower() in {"lost", "closed_lost"}
            and in_window(lead.updated_at, day_start, day_end)
        }
        lost_leads.update(
            {
                event.lead_id
                for event in stage_events
                if (event.to_stage or "").lower() == "lost" and in_window(event.changed_at, day_start, day_end)
            }
        )

        handoff_from_messages = {
            msg.lead_id
            for msg in day_messages
            if normalize_intent(msg.intent, msg.text) == "human_handoff"
        }
        handoff_from_runs = {run.lead_id for run in day_ai_runs if run.handoff_to_human}
        handoff_count = len(handoff_from_messages | handoff_from_runs)

        followup_responses_by_lead: dict[str, datetime] = {}
        for fu in followups:
            if fu.response_at and in_window(fu.response_at, day_start, day_end):
                previous = followup_responses_by_lead.get(fu.lead_id)
                if previous is None or fu.response_at < previous:
                    followup_responses_by_lead[fu.lead_id] = fu.response_at

        inbound_by_lead = defaultdict(list)
        for msg in day_messages:
            if is_inbound(msg):
                inbound_by_lead[msg.lead_id].append(msg.created_at)

        returns_after_followup = 0
        for lead_id, response_time in followup_responses_by_lead.items():
            if any(ts >= response_time for ts in inbound_by_lead.get(lead_id, [])):
                returns_after_followup += 1

        # Include same-day sends and responses if response_at is not modeled.
        for fu in day_followups:
            if fu.response_at is None and inbound_by_lead.get(fu.lead_id):
                returns_after_followup += 1

        return DailyKPI(
            new_leads=new_leads,
            active_dialogs=active_dialogs,
            incoming_messages=incoming,
            outgoing_messages=outgoing,
            new_dialogs=new_dialogs,
            meaningful_conversations=meaningful,
            target_actions=len(target_action_leads),
            lost_leads=len(lost_leads),
            handoff_to_human=handoff_count,
            followup_returns=returns_after_followup,
        )
