from datetime import datetime, timezone

from ai_sales_analytics.analytics.metrics.quality import QualityAnalyticsService
from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    FollowUpRecord,
    MessageRecord,
)


def test_quality_low_confidence_and_handoff_rate() -> None:
    service = QualityAnalyticsService(low_confidence_threshold=0.6)

    day_start = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
    day_end = datetime(2026, 3, 11, 0, 0, tzinfo=timezone.utc)

    messages = [
        MessageRecord(message_id="m1", lead_id="1", created_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), direction="in", role="user", text="price", confidence=0.4),
        MessageRecord(message_id="m2", lead_id="1", created_at=datetime(2026, 3, 10, 10, 1, tzinfo=timezone.utc), direction="out", role="assistant", text="..."),
        MessageRecord(message_id="m3", lead_id="2", created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc), direction="in", role="user", text="human", intent="human_handoff"),
    ]

    ai_runs = [
        AIRunRecord(run_id="r1", lead_id="2", created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc), confidence=0.5, handoff_to_human=True),
    ]

    bookings = [
        BookingRecord(booking_id="b1", lead_id="1", created_at=datetime(2026, 3, 10, 14, 0, tzinfo=timezone.utc), status="confirmed"),
    ]

    followups = [
        FollowUpRecord(followup_id="f1", lead_id="2", sent_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc), response_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)),
    ]

    quality = service.calculate(
        messages=messages,
        ai_runs=ai_runs,
        bookings=bookings,
        stage_events=[],
        followups=followups,
        day_start=day_start,
        day_end=day_end,
    )

    assert quality.low_confidence_rate > 0
    assert quality.handoff_rate > 0
    assert quality.followup_return_rate == 100.0
