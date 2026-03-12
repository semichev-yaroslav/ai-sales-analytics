from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ai_sales_analytics.analytics.models import QualityMetrics
from ai_sales_analytics.analytics.rules import is_inbound, normalize_intent
from ai_sales_analytics.analytics.utils import in_window
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    FollowUpRecord,
    MessageRecord,
    StageEventRecord,
)


class QualityAnalyticsService:
    def __init__(self, low_confidence_threshold: float):
        self.low_confidence_threshold = low_confidence_threshold

    def calculate(
        self,
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        bookings: list[BookingRecord],
        stage_events: list[StageEventRecord],
        followups: list[FollowUpRecord],
        day_start: datetime,
        day_end: datetime,
    ) -> QualityMetrics:
        day_messages = [msg for msg in messages if in_window(msg.created_at, day_start, day_end)]
        day_runs = [run for run in ai_runs if in_window(run.created_at, day_start, day_end)]
        day_bookings = [booking for booking in bookings if in_window(booking.created_at, day_start, day_end)]
        day_stage_events = [event for event in stage_events if in_window(event.changed_at, day_start, day_end)]
        day_followups = [followup for followup in followups if in_window(followup.sent_at, day_start, day_end)]

        active_leads = {msg.lead_id for msg in day_messages}
        active_count = max(len(active_leads), 1)

        low_conf_cases = 0
        total_conf_cases = 0

        for msg in day_messages:
            if msg.confidence is not None:
                total_conf_cases += 1
                if msg.confidence < self.low_confidence_threshold:
                    low_conf_cases += 1
            if normalize_intent(msg.intent, msg.text) == "unclear":
                total_conf_cases += 1
                low_conf_cases += 1

        for run in day_runs:
            if run.confidence is not None:
                total_conf_cases += 1
                if run.confidence < self.low_confidence_threshold:
                    low_conf_cases += 1
            if normalize_intent(run.intent, None) == "unclear":
                total_conf_cases += 1
                low_conf_cases += 1

        low_conf_rate = round((low_conf_cases / total_conf_cases) * 100, 2) if total_conf_cases else 0.0

        bookings_by_lead = defaultdict(list)
        for booking in bookings:
            bookings_by_lead[booking.lead_id].append(booking)
        for items in bookings_by_lead.values():
            items.sort(key=lambda x: x.created_at)

        stage_events_by_lead = defaultdict(list)
        for event in day_stage_events:
            stage_events_by_lead[event.lead_id].append(event)

        day_messages_by_lead = defaultdict(list)
        for msg in day_messages:
            day_messages_by_lead[msg.lead_id].append(msg)

        no_next_step = 0
        no_progress = 0
        handoff_leads = set()

        for lead_id in active_leads:
            lead_msgs = day_messages_by_lead.get(lead_id, [])
            intents = {normalize_intent(msg.intent, msg.text) for msg in lead_msgs if is_inbound(msg)}
            has_booking = bool(day_bookings and any(b.lead_id == lead_id for b in day_bookings))
            has_handoff = any(
                run.lead_id == lead_id and run.handoff_to_human for run in day_runs
            ) or "human_handoff" in intents

            if has_handoff:
                handoff_leads.add(lead_id)

            has_next_step = has_booking or "booking_intent" in intents or has_handoff or "contact_sharing" in intents
            if not has_next_step:
                no_next_step += 1

            has_progress = has_booking or bool(stage_events_by_lead.get(lead_id)) or "booking_intent" in intents
            if not has_progress:
                no_progress += 1

        no_next_step_rate = round((no_next_step / active_count) * 100, 2)
        no_progress_rate = round((no_progress / active_count) * 100, 2)
        handoff_rate = round((len(handoff_leads) / active_count) * 100, 2)

        returns = 0
        sent_count = len(day_followups)
        inbound_day = defaultdict(list)
        for msg in day_messages:
            if is_inbound(msg):
                inbound_day[msg.lead_id].append(msg.created_at)

        for fu in day_followups:
            if fu.response_at and in_window(fu.response_at, day_start, day_end):
                returns += 1
            elif any(ts >= fu.sent_at for ts in inbound_day.get(fu.lead_id, [])):
                returns += 1

        followup_return_rate = round((returns / sent_count) * 100, 2) if sent_count else 0.0

        all_messages_by_lead = defaultdict(list)
        for msg in messages:
            if msg.created_at < day_end:
                all_messages_by_lead[msg.lead_id].append(msg)
        for items in all_messages_by_lead.values():
            items.sort(key=lambda x: x.created_at)

        dialog_lengths = [
            len(all_messages_by_lead[lead_id])
            for lead_id in active_leads
            if all_messages_by_lead.get(lead_id)
        ]
        avg_dialog_length = round(sum(dialog_lengths) / len(dialog_lengths), 2) if dialog_lengths else 0.0

        avg_messages_per_lead = round((len(day_messages) / active_count), 2)

        time_to_key_action_hours = []
        time_to_booking_hours = []

        handoff_timestamps = {}
        for run in ai_runs:
            if run.handoff_to_human:
                existing = handoff_timestamps.get(run.lead_id)
                if existing is None or run.created_at < existing:
                    handoff_timestamps[run.lead_id] = run.created_at

        for lead_id, lead_msgs in all_messages_by_lead.items():
            if not lead_msgs:
                continue

            first_msg_ts = lead_msgs[0].created_at
            booking_ts = bookings_by_lead.get(lead_id, [None])[0]
            booking_dt = booking_ts.created_at if booking_ts else None
            handoff_dt = handoff_timestamps.get(lead_id)

            candidate_actions = [ts for ts in [booking_dt, handoff_dt] if ts is not None]
            if candidate_actions:
                action_ts = min(candidate_actions)
                delta_hours = (action_ts - first_msg_ts).total_seconds() / 3600
                if delta_hours >= 0:
                    time_to_key_action_hours.append(delta_hours)

            if booking_dt is not None:
                booking_delta = (booking_dt - first_msg_ts).total_seconds() / 3600
                if booking_delta >= 0:
                    time_to_booking_hours.append(booking_delta)

        avg_time_to_key_action = (
            round(sum(time_to_key_action_hours) / len(time_to_key_action_hours), 2)
            if time_to_key_action_hours
            else 0.0
        )
        avg_time_to_booking = (
            round(sum(time_to_booking_hours) / len(time_to_booking_hours), 2)
            if time_to_booking_hours
            else 0.0
        )

        return QualityMetrics(
            low_confidence_rate=low_conf_rate,
            no_next_step_rate=no_next_step_rate,
            no_meaningful_progress_rate=no_progress_rate,
            handoff_rate=handoff_rate,
            followup_return_rate=followup_return_rate,
            avg_dialog_length_messages=avg_dialog_length,
            avg_messages_per_lead=avg_messages_per_lead,
            avg_time_to_key_action_hours=avg_time_to_key_action,
            avg_time_first_message_to_booking_hours=avg_time_to_booking,
        )
