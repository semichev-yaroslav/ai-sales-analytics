from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TableMapping(BaseModel):
    table: str
    columns: dict[str, str] = Field(default_factory=dict)


class SchemaMapping(BaseModel):
    leads: TableMapping | None = None
    messages: TableMapping | None = None
    ai_runs: TableMapping | None = None
    bookings: TableMapping | None = None
    stage_events: TableMapping | None = None
    follow_ups: TableMapping | None = None


DEFAULT_MAPPING = SchemaMapping(
    leads=TableMapping(
        table="leads",
        columns={
            "id": "id",
            "created_at": "created_at",
            "updated_at": "updated_at",
            "stage": "stage",
            "status": "status",
            "lost_reason": "lost_reason",
            "target_action_at": "target_action_at",
        },
    ),
    messages=TableMapping(
        table="messages",
        columns={
            "id": "id",
            "lead_id": "lead_id",
            "created_at": "created_at",
            "direction": "direction",
            "role": "role",
            "text": "text",
            "intent": "intent",
            "confidence": "confidence",
            "service_topic": "service_topic",
        },
    ),
    ai_runs=TableMapping(
        table="ai_runs",
        columns={
            "id": "id",
            "lead_id": "lead_id",
            "created_at": "created_at",
            "intent": "intent",
            "confidence": "confidence",
            "handoff_to_human": "handoff_to_human",
            "status": "status",
            "latency_ms": "latency_ms",
            "prompt_tokens": "prompt_tokens",
            "completion_tokens": "completion_tokens",
        },
    ),
    bookings=TableMapping(
        table="bookings",
        columns={
            "id": "id",
            "lead_id": "lead_id",
            "created_at": "created_at",
            "service_name": "service_name",
            "status": "status",
        },
    ),
    stage_events=TableMapping(
        table="stage_events",
        columns={
            "id": "id",
            "lead_id": "lead_id",
            "changed_at": "changed_at",
            "from_stage": "from_stage",
            "to_stage": "to_stage",
        },
    ),
    follow_ups=TableMapping(
        table="follow_ups",
        columns={
            "id": "id",
            "lead_id": "lead_id",
            "sent_at": "sent_at",
            "response_at": "response_at",
        },
    ),
)


def load_schema_mapping(path: str | None) -> SchemaMapping:
    if not path:
        return DEFAULT_MAPPING

    mapping_path = Path(path)
    if not mapping_path.exists():
        return DEFAULT_MAPPING

    payload = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    merged = DEFAULT_MAPPING.model_dump()
    merged.update(payload)
    return SchemaMapping.model_validate(merged)
