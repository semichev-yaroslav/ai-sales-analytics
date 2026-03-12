from datetime import datetime, timezone

from ai_sales_analytics.analytics.metrics.operational import OperationalMetricsService
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    FollowUpRecord,
    LeadRecord,
    MessageRecord,
    StageEventRecord,
)


def dt(hour: int) -> datetime:
    return datetime(2026, 3, 10, hour, 0, tzinfo=timezone.utc)


def test_operational_kpis_basic_day() -> None:
    service = OperationalMetricsService()

    leads = [
        LeadRecord(lead_id="1", created_at=dt(9), updated_at=dt(20), status="new"),
        LeadRecord(lead_id="2", created_at=dt(10), updated_at=dt(21), status="lost"),
    ]
    messages = [
        MessageRecord(message_id="m1", lead_id="1", created_at=dt(9), direction="in", role="user", text="hi"),
        MessageRecord(message_id="m2", lead_id="1", created_at=dt(9), direction="out", role="assistant", text="hello"),
        MessageRecord(message_id="m3", lead_id="1", created_at=dt(11), direction="in", role="user", text="price?"),
        MessageRecord(message_id="m4", lead_id="2", created_at=dt(12), direction="in", role="user", text="human please", intent="human_handoff"),
    ]
    ai_runs = [
        AIRunRecord(run_id="r1", lead_id="2", created_at=dt(12), handoff_to_human=True),
    ]
    bookings = [
        BookingRecord(booking_id="b1", lead_id="1", created_at=dt(15), status="confirmed"),
    ]
    followups = [
        FollowUpRecord(followup_id="f1", lead_id="1", sent_at=dt(14), response_at=dt(16)),
    ]
    stage_events = [
        StageEventRecord(event_id="s1", lead_id="2", changed_at=dt(20), from_stage="qualified", to_stage="lost"),
    ]

    kpi = service.calculate(
        leads=leads,
        messages=messages,
        ai_runs=ai_runs,
        bookings=bookings,
        followups=followups,
        stage_events=stage_events,
        day_start=datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
        day_end=datetime(2026, 3, 11, 0, 0, tzinfo=timezone.utc),
    )

    assert kpi.new_leads == 2
    assert kpi.active_dialogs == 2
    assert kpi.incoming_messages == 3
    assert kpi.outgoing_messages == 1
    assert kpi.target_actions == 1
    assert kpi.lost_leads == 1
    assert kpi.handoff_to_human == 1
