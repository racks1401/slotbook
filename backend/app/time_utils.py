from datetime import date as dt_date, datetime, time, timedelta, timezone
from typing import Tuple

from fastapi import HTTPException, status

# India Standard Time (UTC+05:30)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

OPENING_TIME = time(8, 0)
CLOSING_TIME = time(20, 0)


def get_now_india() -> datetime:
    return datetime.now(IST)


def parse_and_validate_date(date_str: str) -> dt_date:
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Date must be a valid date in YYYY-MM-DD format",
        )


def parse_and_validate_time(time_str: str, field_name: str) -> Tuple[time, str]:
    cleaned = time_str.strip()
    parts = cleaned.split(":")
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a valid time in HH:MM format",
        )
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        t = time(hour, minute)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a valid time",
        )

    # Always normalize to "HH:MM" (e.g. "9:00" -> "09:00")
    normalized = f"{t.hour:02d}:{t.minute:02d}"
    return t, normalized


def time_to_minutes(t_str: str) -> int:
    try:
        parts = t_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0
