from datetime import datetime, timezone

from ai_sales_analytics.analytics.dialog_review import DialogReviewService
from ai_sales_analytics.db.contracts import AIRunRecord, LeadRecord, MessageRecord


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 3, 12, hour, minute, tzinfo=timezone.utc)


def test_dialog_review_flags_risky_dialogs() -> None:
    service = DialogReviewService(low_confidence_threshold=0.55)

    leads = [
        LeadRecord(lead_id="lead-risk", stage="lost", created_at=dt(10)),
        LeadRecord(lead_id="lead-ok", stage="booked", created_at=dt(11)),
    ]

    messages = [
        MessageRecord(
            message_id="m1",
            lead_id="lead-risk",
            created_at=dt(10, 1),
            direction="in",
            role="user",
            text="Не понимаю, что дальше",
        ),
        MessageRecord(
            message_id="m2",
            lead_id="lead-risk",
            created_at=dt(10, 2),
            direction="out",
            role="assistant",
            text="Уточните задачу",
        ),
        MessageRecord(
            message_id="m3",
            lead_id="lead-ok",
            created_at=dt(11, 1),
            direction="in",
            role="user",
            text="Готов записаться на консультацию",
        ),
        MessageRecord(
            message_id="m4",
            lead_id="lead-ok",
            created_at=dt(11, 2),
            direction="out",
            role="assistant",
            text="Отлично, подтверждаю запись",
        ),
    ]

    ai_runs = [
        AIRunRecord(
            run_id="r1",
            lead_id="lead-risk",
            created_at=dt(10, 1),
            intent="unclear",
            confidence=0.33,
        ),
        AIRunRecord(
            run_id="r2",
            lead_id="lead-ok",
            created_at=dt(11, 1),
            intent="booking_intent",
            confidence=0.91,
        ),
    ]

    block = service.build_daily(
        leads=leads,
        messages=messages,
        ai_runs=ai_runs,
        day_start=dt(0),
        day_end=datetime(2026, 3, 13, 0, 0, tzinfo=timezone.utc),
        limit=10,
    )

    assert block.total_dialogs == 2
    assert block.risky_dialogs == 1

    top = block.items[0]
    assert top.lead_id == "lead-risk"
    assert top.risk_score >= 3
    assert any("Лид потерян" in flag for flag in top.risk_flags)
