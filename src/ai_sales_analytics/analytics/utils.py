from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ai_sales_analytics.db.contracts import MessageRecord


def in_window(ts: datetime | None, start: datetime, end: datetime) -> bool:
    if ts is None:
        return False
    return start <= ts < end



def group_messages_by_lead(messages: list[MessageRecord]) -> dict[str, list[MessageRecord]]:
    grouped: dict[str, list[MessageRecord]] = defaultdict(list)
    for msg in messages:
        grouped[msg.lead_id].append(msg)
    for lead_msgs in grouped.values():
        lead_msgs.sort(key=lambda m: m.created_at)
    return grouped
