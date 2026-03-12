from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from ai_sales_analytics.analytics.models import FunnelMetrics
from ai_sales_analytics.analytics.rules import DEFAULT_STAGE_ORDER, normalize_intent
from ai_sales_analytics.analytics.utils import in_window
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    LeadRecord,
    MessageRecord,
    StageEventRecord,
)

TERMINAL_STAGES = {"booked", "lost"}


class FunnelAnalyticsService:
    def __init__(self, stuck_stage_days: int = 3):
        self.stuck_stage_days = stuck_stage_days

    def calculate(
        self,
        leads: list[LeadRecord],
        messages: list[MessageRecord],
        ai_runs: list[AIRunRecord],
        bookings: list[BookingRecord],
        stage_events: list[StageEventRecord],
        day_start: datetime,
        day_end: datetime,
    ) -> FunnelMetrics:
        lead_messages = defaultdict(list)
        for msg in messages:
            if msg.created_at < day_end:
                lead_messages[msg.lead_id].append(msg)

        lead_runs = defaultdict(list)
        for run in ai_runs:
            if run.created_at < day_end:
                lead_runs[run.lead_id].append(run)

        lead_bookings = defaultdict(list)
        for booking in bookings:
            if booking.created_at < day_end:
                lead_bookings[booking.lead_id].append(booking)

        lead_stage_events = defaultdict(list)
        for event in stage_events:
            if event.changed_at < day_end:
                lead_stage_events[event.lead_id].append(event)

        for event_list in lead_stage_events.values():
            event_list.sort(key=lambda e: e.changed_at)

        lead_stage: dict[str, str] = {}
        stage_started_at: dict[str, datetime] = {}

        for lead in leads:
            stage = self._resolve_stage(
                lead=lead,
                lead_messages=lead_messages.get(lead.lead_id, []),
                lead_runs=lead_runs.get(lead.lead_id, []),
                lead_bookings=lead_bookings.get(lead.lead_id, []),
                stage_events=lead_stage_events.get(lead.lead_id, []),
            )
            lead_stage[lead.lead_id] = stage
            stage_started_at[lead.lead_id] = self._stage_start_timestamp(lead, lead_stage_events.get(lead.lead_id, []))

        leads_by_stage = Counter(lead_stage.values())

        daily_transitions = Counter()
        for event in stage_events:
            if in_window(event.changed_at, day_start, day_end):
                from_stage = (event.from_stage or "unknown").strip().lower()
                to_stage = (event.to_stage or "unknown").strip().lower()
                daily_transitions[f"{from_stage}->{to_stage}"] += 1

        if not daily_transitions:
            for lead in leads:
                if lead.target_action_at and in_window(lead.target_action_at, day_start, day_end):
                    daily_transitions["booking_pending->booked"] += 1

        dropoff_points = Counter()
        for event in stage_events:
            if (event.to_stage or "").strip().lower() == "lost":
                from_stage = (event.from_stage or "unknown").strip().lower()
                dropoff_points[from_stage] += 1

        if not dropoff_points:
            for lead in leads:
                if (lead.status or "").lower() in {"lost", "closed_lost"}:
                    origin_stage = ((lead.stage or "unknown").lower() or "unknown")
                    dropoff_points[origin_stage] += 1

        stuck_cutoff = day_end - timedelta(days=self.stuck_stage_days)
        stuck_leads_by_stage = Counter()
        for lead in leads:
            stage = lead_stage.get(lead.lead_id, "unknown")
            started_at = stage_started_at.get(lead.lead_id)
            if stage in TERMINAL_STAGES:
                continue
            if started_at and started_at <= stuck_cutoff:
                stuck_leads_by_stage[stage] += 1

        stage_durations = defaultdict(list)
        for _lead_id, events in lead_stage_events.items():
            if len(events) < 2:
                continue
            for idx in range(len(events) - 1):
                current = events[idx]
                nxt = events[idx + 1]
                stage_name = (current.to_stage or current.from_stage or "unknown").strip().lower()
                duration_hours = (nxt.changed_at - current.changed_at).total_seconds() / 3600
                if duration_hours >= 0:
                    stage_durations[stage_name].append(duration_hours)

        avg_dwell = {
            stage: round(sum(values) / len(values), 2)
            for stage, values in stage_durations.items()
            if values
        }

        conversational_leads = {msg.lead_id for msg in messages if msg.created_at < day_end}
        booked_from_bookings = {
            booking.lead_id
            for booking in bookings
            if booking.created_at < day_end and (booking.status or "confirmed").lower() != "cancelled"
        }
        booked_from_leads = {
            lead.lead_id
            for lead in leads
            if (
                (lead.target_action_at is not None and lead.target_action_at < day_end)
                or (lead.stage or "").strip().lower() == "booked"
            )
        }
        booked_leads = booked_from_bookings | booked_from_leads
        converted_conversational = booked_leads & conversational_leads

        overall_conversion = (
            round((len(converted_conversational) / len(conversational_leads)) * 100, 2)
            if conversational_leads
            else 0.0
        )

        reached_stage = defaultdict(set)
        for lead in leads:
            current = lead_stage.get(lead.lead_id, "unknown")
            current_rank = self._stage_rank(current)
            for stage in DEFAULT_STAGE_ORDER:
                if self._stage_rank(stage) <= current_rank:
                    reached_stage[stage].add(lead.lead_id)

        step_conversion_rates = {}
        for idx in range(len(DEFAULT_STAGE_ORDER) - 1):
            src = DEFAULT_STAGE_ORDER[idx]
            dst = DEFAULT_STAGE_ORDER[idx + 1]
            src_count = len(reached_stage[src])
            dst_count = len(reached_stage[dst])
            rate = round((dst_count / src_count) * 100, 2) if src_count else 0.0
            step_conversion_rates[f"{src}->{dst}"] = rate

        return FunnelMetrics(
            leads_by_stage=dict(leads_by_stage),
            stage_transitions=dict(daily_transitions),
            stuck_leads_by_stage=dict(stuck_leads_by_stage),
            avg_stage_dwell_hours=avg_dwell,
            overall_conversion_rate=overall_conversion,
            conversion_target_actions=len(converted_conversational),
            conversion_conversational_leads=len(conversational_leads),
            conversion_formula="конверсия = лиды с целевым действием / лиды с диалогом * 100%",
            step_conversion_rates=step_conversion_rates,
            dropoff_points=dict(dropoff_points),
        )

    def _resolve_stage(
        self,
        lead: LeadRecord,
        lead_messages: list[MessageRecord],
        lead_runs: list[AIRunRecord],
        lead_bookings: list[BookingRecord],
        stage_events: list[StageEventRecord],
    ) -> str:
        if stage_events:
            latest = max(stage_events, key=lambda e: e.changed_at)
            if latest.to_stage:
                return latest.to_stage.strip().lower()

        if lead.stage:
            return lead.stage.strip().lower()

        if any((booking.status or "confirmed").lower() != "cancelled" for booking in lead_bookings):
            return "booked"

        if (lead.status or "").lower() in {"lost", "closed_lost"}:
            return "lost"

        intents = [normalize_intent(msg.intent, msg.text) for msg in lead_messages]
        intents.extend([normalize_intent(run.intent, None) for run in lead_runs if run.intent])

        if "booking_intent" in intents:
            return "booking_pending"
        if "objection" in intents:
            return "objection"
        if "price_question" in intents:
            return "qualified"
        if intents:
            return "interested"
        return "new"

    @staticmethod
    def _stage_start_timestamp(lead: LeadRecord, stage_events: list[StageEventRecord]) -> datetime | None:
        if stage_events:
            latest = max(stage_events, key=lambda e: e.changed_at)
            return latest.changed_at
        return lead.updated_at or lead.created_at

    @staticmethod
    def _stage_rank(stage: str) -> int:
        try:
            return DEFAULT_STAGE_ORDER.index(stage)
        except ValueError:
            if stage == "lost":
                return len(DEFAULT_STAGE_ORDER)
            return 0
