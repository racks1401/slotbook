from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Room, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter()


def is_end_after_start(start_str: str, end_str: str) -> bool:
    start_str = start_str.strip()
    end_str = end_str.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            s = datetime.strptime(start_str, fmt).time()
            e = datetime.strptime(end_str, fmt).time()
            return e > s
        except ValueError:
            continue
    return end_str > start_str


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_end_after_start(data.start_time, data.end_time):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End time must be after start time",
        )

    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    booking = Booking(
        room_id=data.room_id,
        user_id=current_user.id,
        date=data.date.strip(),
        start_time=data.start_time.strip(),
        end_time=data.end_time.strip(),
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
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.date.desc(), Booking.start_time.desc())
        .all()
    )
