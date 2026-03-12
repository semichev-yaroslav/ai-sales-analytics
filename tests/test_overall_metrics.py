from datetime import datetime, timezone

from ai_sales_analytics.analytics.metrics.overall import OverallMetricsService
from ai_sales_analytics.db.contracts import AIRunRecord, LeadRecord, MessageRecord


def dt(day: int, hour: int) -> datetime:
    return datetime(2026, 3, day, hour, 0, tzinfo=timezone.utc)


def test_overall_metrics_conversion_and_totals() -> None:
    service = OverallMetricsService()

    leads = [
        LeadRecord(lead_id="1", created_at=dt(1, 9), stage="booked", target_action_at=dt(1, 11)),
        LeadRecord(lead_id="2", created_at=dt(2, 9), stage="lost"),
        LeadRecord(lead_id="3", created_at=dt(3, 9), stage="interested"),
    ]
    messages = [
        MessageRecord(message_id="m1", lead_id="1", created_at=dt(1, 9), direction="in", role="user", text="hi"),
        MessageRecord(message_id="m2", lead_id="1", created_at=dt(1, 9), direction="out", role="assistant", text="ok"),
        MessageRecord(message_id="m3", lead_id="2", created_at=dt(2, 9), direction="in", role="user", text="дорого"),
        MessageRecord(message_id="m4", lead_id="2", created_at=dt(2, 9), direction="out", role="assistant", text="понимаю"),
        MessageRecord(message_id="m5", lead_id="3", created_at=dt(3, 9), direction="in", role="user", text="интересно"),
    ]
    ai_runs = [
        AIRunRecord(run_id="r1", lead_id="2", created_at=dt(2, 9), intent="objection", confidence=0.7),
    ]

    overall = service.calculate(
        leads=leads,
        messages=messages,
        ai_runs=ai_runs,
        bookings=[],
        followups=[],
        day_end=datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc),
    )

    assert overall.total_leads == 3
    assert overall.total_dialogs == 3
    assert overall.total_target_actions == 1
    assert overall.conversion_numerator == 1
    assert overall.conversion_denominator == 3
    assert overall.overall_conversion_rate == 33.33
