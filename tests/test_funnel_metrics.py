from datetime import datetime, timezone

from ai_sales_analytics.analytics.metrics.funnel import FunnelAnalyticsService
from ai_sales_analytics.db.contracts import (
    BookingRecord,
    LeadRecord,
    MessageRecord,
    StageEventRecord,
)


def test_funnel_conversion_and_dropoff() -> None:
    service = FunnelAnalyticsService(stuck_stage_days=2)

    day_start = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
    day_end = datetime(2026, 3, 11, 0, 0, tzinfo=timezone.utc)

    leads = [
        LeadRecord(lead_id="1", created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc), stage="booked"),
        LeadRecord(lead_id="2", created_at=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc), stage="lost"),
        LeadRecord(lead_id="3", created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc), stage="qualified", updated_at=datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc)),
    ]

    messages = [
        MessageRecord(message_id="m1", lead_id="1", created_at=datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc), direction="in", role="user", text=""),
        MessageRecord(message_id="m2", lead_id="2", created_at=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc), direction="in", role="user", text=""),
        MessageRecord(message_id="m3", lead_id="3", created_at=datetime(2026, 3, 3, 11, 0, tzinfo=timezone.utc), direction="in", role="user", text=""),
    ]

    bookings = [
        BookingRecord(booking_id="b1", lead_id="1", created_at=datetime(2026, 3, 10, 13, 0, tzinfo=timezone.utc), status="confirmed"),
    ]

    stage_events = [
        StageEventRecord(event_id="s1", lead_id="1", changed_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc), from_stage="booking_pending", to_stage="booked"),
        StageEventRecord(event_id="s2", lead_id="2", changed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), from_stage="objection", to_stage="lost"),
    ]

    funnel = service.calculate(
        leads=leads,
        messages=messages,
        ai_runs=[],
        bookings=bookings,
        stage_events=stage_events,
        day_start=day_start,
        day_end=day_end,
    )

    assert funnel.overall_conversion_rate > 0
    assert funnel.leads_by_stage["booked"] == 1
    assert funnel.dropoff_points.get("objection") == 1
    assert "booking_pending->booked" in funnel.stage_transitions
