from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(slots=True)
class TimeWindow:
    start: datetime
    end: datetime


def daily_window(target_date: date, timezone_name: str) -> TimeWindow:
    tz = ZoneInfo(timezone_name)
    start = datetime.combine(target_date, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return TimeWindow(start=start, end=end)


def lookback_window(target_date: date, timezone_name: str, lookback_days: int) -> TimeWindow:
    day = daily_window(target_date, timezone_name)
    return TimeWindow(start=day.start - timedelta(days=lookback_days), end=day.end)
