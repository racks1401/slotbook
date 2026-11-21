from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import Booking, Room, User
from app.schemas import BookingResponse, RoomCreate, RoomResponse, RoomUpdate
from app.time_utils import get_now_india, time_to_minutes

router = APIRouter()


@router.get("", response_model=List[RoomResponse])
@router.get("/", response_model=List[RoomResponse], include_in_schema=False)
def get_rooms(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Room)
    if not include_inactive:
        query = query.filter(Room.is_active == True)
    return query.all()


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
    include_all: bool = Query(False, description="Include cancelled or rejected bookings"),
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
    if not include_all:
        query = query.filter(Booking.status.in_(["confirmed", "pending"]))
    bookings = query.all()
    # Sort by real time
    bookings.sort(key=lambda b: time_to_minutes(b.start_time))
    return bookings


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_room(
    data: RoomCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    existing = db.query(Room).filter(Room.name == data.name.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room with this name already exists",
        )

    room = Room(
        name=data.name.strip(),
        building=data.building.strip(),
        capacity=data.capacity,
        is_active=data.is_active,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def check_room_has_future_bookings(room_id: int, db: Session) -> bool:
    now = get_now_india()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")

    future_booking = (
        db.query(Booking)
        .filter(
            Booking.room_id == room_id,
            Booking.status.in_(["confirmed", "pending"]),
            or_(
                Booking.date > today_str,
                and_(Booking.date == today_str, Booking.end_time > current_time_str),
            ),
        )
        .first()
    )
    return future_booking is not None


@router.put("/{id}", response_model=RoomResponse)
@router.patch("/{id}", response_model=RoomResponse)
def update_room(
    id: int,
    data: RoomUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    if data.name is not None and data.name.strip() != room.name:
        existing = db.query(Room).filter(Room.name == data.name.strip(), Room.id != id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room with this name already exists",
            )
        room.name = data.name.strip()

    if data.building is not None:
        room.building = data.building.strip()

    if data.capacity is not None:
        room.capacity = data.capacity

    if data.is_active is False and room.is_active is True:
        if check_room_has_future_bookings(id, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot close room with future confirmed or pending bookings",
            )
        room.is_active = False
    elif data.is_active is True:
        room.is_active = True

    db.commit()
    db.refresh(room)
    return room


@router.post("/{id}/close", response_model=RoomResponse)
def close_room(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    if check_room_has_future_bookings(id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot close room with future confirmed or pending bookings",
        )

    room.is_active = False
    db.commit()
    db.refresh(room)
    return room
