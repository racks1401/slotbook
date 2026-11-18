from app.auth import hash_password, create_access_token
from app.models import User


def test_register_user_works(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "New Student",
            "email": "NEWSTUDENT@college.edu",
            "password": "securepassword",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Student"
    assert data["email"] == "newstudent@college.edu"
    assert data["role"] == "student"
    assert "id" in data


def test_login_right_password_returns_token(client, test_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "student1@college.edu",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client, test_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "student1@college.edu",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_rooms_without_token_rejected(client):
    response = client.get("/rooms")
    assert response.status_code == 401


def test_create_booking_returns_201(client, auth_headers, test_room):
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": "2026-11-20",
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Physics Lab Project Discussion",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == test_room.id
    assert data["status"] == "confirmed"
    assert data["purpose"] == "Physics Lab Project Discussion"
    assert data["date"] == "2026-11-20"
    assert data["start_time"] == "10:00"
    assert data["end_time"] == "11:00"


def test_booking_end_time_before_start_time_returns_422(client, auth_headers, test_room):
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": "2026-11-20",
            "start_time": "14:00",
            "end_time": "11:00",
            "purpose": "Invalid time slot",
        },
    )
    assert response.status_code == 422


def test_get_my_bookings_shows_only_mine(client, auth_headers, test_user, test_room, db_session):
    # 1. Create a second student user
    user2 = User(
        name="Student Two",
        email="student2@college.edu",
        password_hash=hash_password("password456"),
        role="student",
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    user2_token = create_access_token(data={"sub": str(user2.id)})
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # 2. Book room as user 1
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": "2026-11-21",
            "start_time": "09:00",
            "end_time": "10:00",
            "purpose": "User 1 Booking",
        },
    )
    assert res1.status_code == 201

    # 3. Book room as user 2
    res2 = client.post(
        "/bookings",
        headers=user2_headers,
        json={
            "room_id": test_room.id,
            "date": "2026-11-22",
            "start_time": "14:00",
            "end_time": "15:00",
            "purpose": "User 2 Booking",
        },
    )
    assert res2.status_code == 201

    # 4. Fetch bookings for user 1 -> should only show User 1's booking
    res_mine1 = client.get("/bookings/mine", headers=auth_headers)
    assert res_mine1.status_code == 200
    my_bookings1 = res_mine1.json()
    assert len(my_bookings1) == 1
    assert my_bookings1[0]["purpose"] == "User 1 Booking"

    # 5. Fetch bookings for user 2 -> should only show User 2's booking
    res_mine2 = client.get("/bookings/mine", headers=user2_headers)
    assert res_mine2.status_code == 200
    my_bookings2 = res_mine2.json()
    assert len(my_bookings2) == 1
    assert my_bookings2[0]["purpose"] == "User 2 Booking"
