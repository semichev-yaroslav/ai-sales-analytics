from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class LeadRecord:
    lead_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    stage: str | None = None
    status: str | None = None
    lost_reason: str | None = None
    target_action_at: datetime | None = None


@dataclass(slots=True)
class MessageRecord:
    message_id: str
    lead_id: str
    created_at: datetime
    direction: str | None = None
    role: str | None = None
    text: str | None = None
    intent: str | None = None
    confidence: float | None = None
    service_topic: str | None = None


@dataclass(slots=True)
class AIRunRecord:
    run_id: str
    lead_id: str
    created_at: datetime
    intent: str | None = None
    confidence: float | None = None
    handoff_to_human: bool | None = None
    status: str | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(slots=True)
class BookingRecord:
    booking_id: str
    lead_id: str
    created_at: datetime
    service_name: str | None = None
    status: str | None = None


@dataclass(slots=True)
class StageEventRecord:
    event_id: str
    lead_id: str
    changed_at: datetime
    from_stage: str | None = None
    to_stage: str | None = None


@dataclass(slots=True)
class FollowUpRecord:
    followup_id: str
    lead_id: str
    sent_at: datetime
    response_at: datetime | None = None


@dataclass(slots=True)
class DataBundle:
    leads: list[LeadRecord] = field(default_factory=list)
    messages: list[MessageRecord] = field(default_factory=list)
    ai_runs: list[AIRunRecord] = field(default_factory=list)
    bookings: list[BookingRecord] = field(default_factory=list)
    stage_events: list[StageEventRecord] = field(default_factory=list)
    followups: list[FollowUpRecord] = field(default_factory=list)
