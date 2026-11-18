from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    building: str
    capacity: int
    is_active: bool


class BookingCreate(BaseModel):
    room_id: int
    date: str
    start_time: str
    end_time: str
    purpose: str = Field(..., max_length=200)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_id: int
    date: str
    start_time: str
    end_time: str
    purpose: str
    status: str
    created_at: datetime
    room: Optional[RoomResponse] = None
