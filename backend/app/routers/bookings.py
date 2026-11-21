from datetime import timedelta
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import Booking, Room, User
from app.schemas import BookingCreate, BookingResponse
from app.time_utils import (
    CLOSING_TIME,
    OPENING_TIME,
    get_now_india,
    parse_and_validate_date,
    parse_and_validate_time,
    time_to_minutes,
)

router = APIRouter()


@router.post("", response_model=Union[BookingResponse, List[BookingResponse]], status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=Union[BookingResponse, List[BookingResponse]], status_code=status.HTTP_201_CREATED, include_in_schema=False)
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
    now_india = get_now_india()
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

    # 8. At most 14 days ahead
    max_allowed_date = today_india + timedelta(days=14)
    if booking_date > max_allowed_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookings can only be made up to 14 days in advance",
        )

    # 9. Check room exists and is active
    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    if not room.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book an inactive room",
        )

    # 10. Approval flow: rooms with capacity >= 60 start as "pending", others as "confirmed"
    initial_status = "pending" if room.capacity >= 60 else "confirmed"

    # 11. Recurring bookings: repeat weekly for N weeks (N between 2 and 8)
    if data.repeat_weeks is not None:
        if data.repeat_weeks < 2 or data.repeat_weeks > 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="repeat_weeks must be between 2 and 8",
            )
        dates_to_book = [booking_date + timedelta(days=7 * k) for k in range(data.repeat_weeks)]
    else:
        dates_to_book = [booking_date]

    # 12. Daily limit: one student can hold at most 4 hours (240 minutes) of active bookings per day across all rooms
    if current_user.role != "admin":
        for d in dates_to_book:
            d_str = d.strftime("%Y-%m-%d")
            active_student_bookings = (
                db.query(Booking)
                .filter(
                    Booking.user_id == current_user.id,
                    Booking.date == d_str,
                    Booking.status.in_(["confirmed", "pending"]),
                )
                .all()
            )
            existing_minutes = sum(
                time_to_minutes(b.end_time) - time_to_minutes(b.start_time)
                for b in active_student_bookings
            )
            if existing_minutes + duration_minutes > 240:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Daily booking limit of 4 hours exceeded for {d_str}",
                )

    # 13. Clash check across all dates (in one transaction, all-or-nothing)
    clashing_dates = []
    first_clash_detail = ""
    for d in dates_to_book:
        d_str = d.strftime("%Y-%m-%d")
        existing_bookings = (
            db.query(Booking)
            .filter(
                Booking.room_id == data.room_id,
                Booking.date == d_str,
                Booking.status.in_(["confirmed", "pending"]),
            )
            .all()
        )
        for b in existing_bookings:
            if norm_start < b.end_time and norm_end > b.start_time:
                clashing_dates.append(d_str)
                if not first_clash_detail:
                    first_clash_detail = f"Slot {b.start_time}-{b.end_time} is already booked"
                break

    if clashing_dates:
        if data.repeat_weeks is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Clashing dates: {', '.join(clashing_dates)}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=first_clash_detail,
            )

    # 14. Save bookings in one transaction
    created_bookings = []
    for d in dates_to_book:
        d_str = d.strftime("%Y-%m-%d")
        booking = Booking(
            room_id=data.room_id,
            user_id=current_user.id,
            date=d_str,
            start_time=norm_start,
            end_time=norm_end,
            purpose=data.purpose.strip(),
            status=initial_status,
        )
        db.add(booking)
        created_bookings.append(booking)

    db.commit()
    for b in created_bookings:
        db.refresh(b)

    if data.repeat_weeks is not None:
        return created_bookings
    return created_bookings[0]


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


@router.get("/pending", response_model=List[BookingResponse])
@router.get("/pending/", response_model=List[BookingResponse], include_in_schema=False)
def get_pending_bookings(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    bookings = db.query(Booking).filter(Booking.status == "pending").all()
    # Sort by real time chronologically
    bookings.sort(key=lambda b: time_to_minutes(b.start_time))
    bookings.sort(key=lambda b: b.date)
    return bookings


@router.post("/{id}/approve", response_model=BookingResponse)
def approve_booking(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending bookings can be approved",
        )

    # Re-check clashes against confirmed bookings
    existing = (
        db.query(Booking)
        .filter(
            Booking.room_id == booking.room_id,
            Booking.date == booking.date,
            Booking.status == "confirmed",
            Booking.id != booking.id,
        )
        .all()
    )
    for b in existing:
        if booking.start_time < b.end_time and booking.end_time > b.start_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot {b.start_time}-{b.end_time} is already booked",
            )

    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{id}/reject", response_model=BookingResponse)
def reject_booking(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending bookings can be rejected",
        )

    booking.status = "rejected"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{id}/cancel", response_model=BookingResponse)
@router.delete("/{id}", response_model=BookingResponse)
def cancel_booking(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Admin can cancel any booking; student can only cancel their own
    if current_user.role != "admin" and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another user's booking",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
        )

    # Student can cancel their own booking only before it starts
    if current_user.role != "admin":
        now_india = get_now_india()
        today_india = now_india.date()
        current_time_india = now_india.time()

        b_date = parse_and_validate_date(booking.date)
        b_start, _ = parse_and_validate_time(booking.start_time, "Start time")

        if b_date < today_india or (b_date == today_india and b_start <= current_time_india):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a booking that has already started or passed",
            )

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
