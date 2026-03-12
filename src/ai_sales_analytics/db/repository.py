from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from dateutil import parser
from sqlalchemy import MetaData, Table, inspect, select
from sqlalchemy.engine import Engine

from ai_sales_analytics.db.contracts import (
    AIRunRecord,
    BookingRecord,
    DataBundle,
    FollowUpRecord,
    LeadRecord,
    MessageRecord,
    StageEventRecord,
)
from ai_sales_analytics.db.schema_mapping import SchemaMapping, TableMapping

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Read-only repository with schema-adapter support."""

    def __init__(self, engine: Engine, mapping: SchemaMapping):
        self.engine = engine
        self.mapping = mapping
        self._inspector = inspect(engine)
        self._table_cache: dict[str, Table] = {}

    def fetch_bundle(self, history_start: datetime, end: datetime) -> DataBundle:
        return DataBundle(
            leads=self.fetch_leads_snapshot(end),
            messages=self.fetch_messages(history_start, end),
            ai_runs=self.fetch_ai_runs(history_start, end),
            bookings=self.fetch_bookings(history_start, end),
            stage_events=self.fetch_stage_events(history_start, end),
            followups=self.fetch_followups(history_start, end),
        )

    def fetch_leads_snapshot(self, end: datetime) -> list[LeadRecord]:
        rows = self._select_rows(
            table_mapping=self.mapping.leads,
            end=end,
            time_key="created_at",
            only_before_end=True,
        )
        return [rec for rec in (self._row_to_lead(row) for row in rows) if rec]

    def fetch_messages(self, start: datetime, end: datetime) -> list[MessageRecord]:
        rows = self._select_rows(self.mapping.messages, start=start, end=end, time_key="created_at")
        return [rec for rec in (self._row_to_message(row) for row in rows) if rec]

    def fetch_ai_runs(self, start: datetime, end: datetime) -> list[AIRunRecord]:
        rows = self._select_rows(self.mapping.ai_runs, start=start, end=end, time_key="created_at")
        return [rec for rec in (self._row_to_ai_run(row) for row in rows) if rec]

    def fetch_bookings(self, start: datetime, end: datetime) -> list[BookingRecord]:
        rows = self._select_rows(self.mapping.bookings, start=start, end=end, time_key="created_at")
        return [rec for rec in (self._row_to_booking(row) for row in rows) if rec]

    def fetch_stage_events(self, start: datetime, end: datetime) -> list[StageEventRecord]:
        rows = self._select_rows(self.mapping.stage_events, start=start, end=end, time_key="changed_at")
        return [rec for rec in (self._row_to_stage_event(row) for row in rows) if rec]

    def fetch_followups(self, start: datetime, end: datetime) -> list[FollowUpRecord]:
        rows = self._select_rows(self.mapping.follow_ups, start=start, end=end, time_key="sent_at")
        return [rec for rec in (self._row_to_followup(row) for row in rows) if rec]

    def _select_rows(
        self,
        table_mapping: TableMapping | None,
        start: datetime | None = None,
        end: datetime | None = None,
        time_key: str | None = None,
        only_before_end: bool = False,
    ) -> list[dict[str, Any]]:
        if table_mapping is None:
            return []

        table = self._get_table(table_mapping.table)
        if table is None:
            return []

        selected_columns: dict[str, Any] = {}
        for canonical_name, db_column_name in table_mapping.columns.items():
            if db_column_name in table.c:
                selected_columns[canonical_name] = table.c[db_column_name]

        if not selected_columns:
            logger.warning("No mapped columns found for table '%s'", table_mapping.table)
            return []

        stmt = select(*[col.label(alias) for alias, col in selected_columns.items()])

        if time_key and time_key in selected_columns:
            time_column = selected_columns[time_key]
            if start is not None and not only_before_end:
                stmt = stmt.where(time_column >= start)
            if end is not None:
                stmt = stmt.where(time_column < end)
        elif only_before_end and end is not None and time_key:
            logger.warning(
                "Time key '%s' is not mapped for table '%s'; cannot filter by end boundary.",
                time_key,
                table_mapping.table,
            )

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        return [dict(row) for row in rows]

    def _get_table(self, table_name: str) -> Table | None:
        if table_name in self._table_cache:
            return self._table_cache[table_name]

        if not self._inspector.has_table(table_name):
            logger.warning("Table '%s' not found in bot DB. Analytics block will degrade gracefully.", table_name)
            return None

        table = Table(table_name, MetaData(), autoload_with=self.engine)
        self._table_cache[table_name] = table
        return table

    @staticmethod
    def _parse_datetime(raw: Any) -> datetime | None:
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, str):
            try:
                parsed = parser.isoparse(raw)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _to_str(raw: Any) -> str | None:
        if raw is None:
            return None
        return str(raw)

    @staticmethod
    def _to_float(raw: Any) -> float | None:
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(raw: Any) -> int | None:
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_bool(raw: Any) -> bool | None:
        if raw is None:
            return None
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, dict):
            bool_keys = [
                "handoff_to_human",
                "handoff_to_admin",
                "handoff",
                "requires_human",
            ]
            for key in bool_keys:
                value = raw.get(key)
                if isinstance(value, bool):
                    return value
                if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
                    return True
            action_value = raw.get("assistant_action") or raw.get("action")
            if isinstance(action_value, str) and action_value.strip().lower() in {
                "handoff",
                "human_handoff",
                "transfer_to_human",
            }:
                return True
            return None
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "yes", "y", "t"}:
                return True
            if normalized in {"handoff", "human_handoff", "transfer_to_human"}:
                return True
            return False
        return None

    def _row_to_lead(self, row: dict[str, Any]) -> LeadRecord | None:
        lead_id = self._to_str(row.get("id"))
        if not lead_id:
            return None
        return LeadRecord(
            lead_id=lead_id,
            created_at=self._parse_datetime(row.get("created_at")),
            updated_at=self._parse_datetime(row.get("updated_at")),
            stage=self._to_str(row.get("stage")),
            status=self._to_str(row.get("status")),
            lost_reason=self._to_str(row.get("lost_reason")),
            target_action_at=self._parse_datetime(row.get("target_action_at")),
        )

    def _row_to_message(self, row: dict[str, Any]) -> MessageRecord | None:
        message_id = self._to_str(row.get("id"))
        lead_id = self._to_str(row.get("lead_id"))
        created_at = self._parse_datetime(row.get("created_at"))
        if not message_id or not lead_id or not created_at:
            return None
        return MessageRecord(
            message_id=message_id,
            lead_id=lead_id,
            created_at=created_at,
            direction=self._to_str(row.get("direction")),
            role=self._to_str(row.get("role")),
            text=self._to_str(row.get("text")),
            intent=self._to_str(row.get("intent")),
            confidence=self._to_float(row.get("confidence")),
            service_topic=self._to_str(row.get("service_topic")),
        )

    def _row_to_ai_run(self, row: dict[str, Any]) -> AIRunRecord | None:
        run_id = self._to_str(row.get("id"))
        lead_id = self._to_str(row.get("lead_id"))
        created_at = self._parse_datetime(row.get("created_at"))
        if not run_id or not lead_id or not created_at:
            return None
        return AIRunRecord(
            run_id=run_id,
            lead_id=lead_id,
            created_at=created_at,
            intent=self._to_str(row.get("intent")),
            confidence=self._to_float(row.get("confidence")),
            handoff_to_human=self._to_bool(row.get("handoff_to_human")),
            status=self._to_str(row.get("status")),
            latency_ms=self._to_float(row.get("latency_ms")),
            prompt_tokens=self._to_int(row.get("prompt_tokens")),
            completion_tokens=self._to_int(row.get("completion_tokens")),
        )

    def _row_to_booking(self, row: dict[str, Any]) -> BookingRecord | None:
        booking_id = self._to_str(row.get("id"))
        lead_id = self._to_str(row.get("lead_id"))
        created_at = self._parse_datetime(row.get("created_at"))
        if not booking_id or not lead_id or not created_at:
            return None
        return BookingRecord(
            booking_id=booking_id,
            lead_id=lead_id,
            created_at=created_at,
            service_name=self._to_str(row.get("service_name")),
            status=self._to_str(row.get("status")),
        )

    def _row_to_stage_event(self, row: dict[str, Any]) -> StageEventRecord | None:
        event_id = self._to_str(row.get("id"))
        lead_id = self._to_str(row.get("lead_id"))
        changed_at = self._parse_datetime(row.get("changed_at"))
        if not lead_id or not changed_at:
            return None
        return StageEventRecord(
            event_id=event_id or f"stage-{lead_id}-{changed_at.isoformat()}",
            lead_id=lead_id,
            changed_at=changed_at,
            from_stage=self._to_str(row.get("from_stage")),
            to_stage=self._to_str(row.get("to_stage")),
        )

    def _row_to_followup(self, row: dict[str, Any]) -> FollowUpRecord | None:
        followup_id = self._to_str(row.get("id"))
        lead_id = self._to_str(row.get("lead_id"))
        sent_at = self._parse_datetime(row.get("sent_at"))
        if not lead_id or not sent_at:
            return None
        return FollowUpRecord(
            followup_id=followup_id or f"followup-{lead_id}-{sent_at.isoformat()}",
            lead_id=lead_id,
            sent_at=sent_at,
            response_at=self._parse_datetime(row.get("response_at")),
        )
