import os
from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Room, User

SEED_ROOMS = [
    {
        "name": "Turing Computing Lab",
        "building": "Science & Tech Block",
        "capacity": 40,
        "is_active": True,
    },
    {
        "name": "Aryabhata Seminar Hall",
        "building": "Main Academic Block",
        "capacity": 120,
        "is_active": True,
    },
    {
        "name": "Library Discussion Room A",
        "building": "Central Library",
        "capacity": 8,
        "is_active": True,
    },
    {
        "name": "Electronics & IoT Lab",
        "building": "Engineering Wing",
        "capacity": 35,
        "is_active": True,
    },
    {
        "name": "Library Discussion Room B",
        "building": "Central Library",
        "capacity": 12,
        "is_active": True,
    },
]


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin_email = "admin@college.edu"
        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            admin_password = "admin123"
            print("Notice: ADMIN_PASSWORD environment variable not set. Using default 'admin123'.")

        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin = User(
                name="Admin User",
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
            )
            db.add(admin)
            print(f"Created admin user: {admin_email}")
        else:
            print(f"Admin user already exists: {admin_email}")

        for room_data in SEED_ROOMS:
            existing_room = db.query(Room).filter(Room.name == room_data["name"]).first()
            if not existing_room:
                room = Room(**room_data)
                db.add(room)
                print(f"Created room: {room_data['name']} ({room_data['building']}, capacity {room_data['capacity']})")
            else:
                print(f"Room already exists: {room_data['name']}")

        db.commit()
        print("\nDatabase seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
