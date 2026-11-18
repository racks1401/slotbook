from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Room, User
from app.schemas import BookingResponse, RoomResponse

router = APIRouter()


@router.get("", response_model=List[RoomResponse])
@router.get("/", response_model=List[RoomResponse], include_in_schema=False)
def get_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Room).filter(Room.is_active == True).all()


@router.get("/{id}", response_model=RoomResponse)
def get_room(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    return room


@router.get("/{id}/bookings", response_model=List[BookingResponse])
def get_room_bookings(
    id: int,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    query = db.query(Booking).filter(Booking.room_id == id)
    if date:
        query = query.filter(Booking.date == date.strip())
    return query.order_by(Booking.start_time.asc()).all()
