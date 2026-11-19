from datetime import date as dt_date, datetime, time, timedelta, timezone
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Room, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter()

# India Standard Time (UTC+05:30)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

OPENING_TIME = time(8, 0)
CLOSING_TIME = time(20, 0)


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


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Validate date format
    booking_date = parse_and_validate_date(data.date)

    # 2. Validate time format & normalize (e.g. "9:00" -> "09:00")
    start_t, norm_start = parse_and_validate_time(data.start_time, "Start time")
    end_t, norm_end = parse_and_validate_time(data.end_time, "End time")

    # 3. Bookings must start and end on a 30-minute mark
    if start_t.minute not in (0, 30) or end_t.minute not in (0, 30):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookings must start and end on a 30-minute mark (e.g. 09:00 or 09:30)",
        )

    # 4. Rooms open 08:00 to 20:00
    if start_t < OPENING_TIME or end_t > CLOSING_TIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rooms are open from 08:00 to 20:00",
        )

    # 5. End time must be after start time
    if end_t <= start_t:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End time must be after start time",
        )

    # 6. Duration: at least 30 minutes and at most 3 hours (180 minutes)
    duration_minutes = (end_t.hour * 60 + end_t.minute) - (start_t.hour * 60 + start_t.minute)
    if duration_minutes < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookings must last at least 30 minutes",
        )
    if duration_minutes > 180:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookings cannot exceed 3 hours",
        )

    # 7. No bookings in the past, using India time (Asia/Kolkata)
    now_india = datetime.now(IST)
    today_india = now_india.date()
    current_time_india = now_india.time()

    if booking_date < today_india:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot book a date in the past",
        )
    if booking_date == today_india and start_t < current_time_india:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot book a time slot in the past",
        )

    # 8. Check room exists
    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    # 9. Clash check: cannot overlap another confirmed booking for the same room on the same day
    normalized_date = data.date.strip()
    existing_bookings = (
        db.query(Booking)
        .filter(
            Booking.room_id == data.room_id,
            Booking.date == normalized_date,
            Booking.status == "confirmed",
        )
        .all()
    )

    for b in existing_bookings:
        # Overlap check: (start < b.end_time) and (end > b.start_time)
        # With normalized "HH:MM", string comparison matches real time comparison
        if norm_start < b.end_time and norm_end > b.start_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot {b.start_time}-{b.end_time} is already booked",
            )

    # 10. Save booking with normalized date and times
    booking = Booking(
        room_id=data.room_id,
        user_id=current_user.id,
        date=normalized_date,
        start_time=norm_start,
        end_time=norm_end,
        purpose=data.purpose.strip(),
        status="confirmed",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/mine", response_model=List[BookingResponse])
@router.get("/mine/", response_model=List[BookingResponse], include_in_schema=False)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    # Sort by real time: earliest start time first, then newest date first (stable sort)
    bookings.sort(key=lambda b: time_to_minutes(b.start_time))
    bookings.sort(key=lambda b: b.date, reverse=True)
    return bookings
