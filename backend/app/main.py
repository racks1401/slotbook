from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import Base, engine
import app.models  # Register models with Base metadata
from app.routers import auth, bookings, rooms

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SlotBook API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])


@app.get("/health")
def health():
    return {"status": "ok"}
