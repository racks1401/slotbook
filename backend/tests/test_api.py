from datetime import datetime, timedelta, timezone
from app.auth import hash_password, create_access_token
from app.models import User

IST = timezone(timedelta(hours=5, minutes=30))


def get_future_date(days=2) -> str:
    return (datetime.now(IST) + timedelta(days=days)).strftime("%Y-%m-%d")


def get_past_date(days=2) -> str:
    return (datetime.now(IST) - timedelta(days=days)).strftime("%Y-%m-%d")


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


def test_create_booking_valid_returns_201(client, auth_headers, test_room):
    future_date = get_future_date(2)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
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
    assert data["date"] == future_date
    assert data["start_time"] == "10:00"
    assert data["end_time"] == "11:00"


def test_create_booking_normalizes_time(client, auth_headers, test_room):
    # Accepts "9:00" and always saves as "09:00"
    future_date = get_future_date(3)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "9:00",
            "end_time": "10:30",
            "purpose": "Morning algorithms study",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["start_time"] == "09:00"
    assert data["end_time"] == "10:30"


def test_booking_invalid_date_format_returns_422(client, auth_headers, test_room):
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": "invalid-date-format",
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Bad date format",
        },
    )
    assert response.status_code == 422


def test_booking_invalid_time_format_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(2)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "25:00",
            "end_time": "11:00",
            "purpose": "Bad time format",
        },
    )
    assert response.status_code == 422


def test_booking_outside_opening_hours_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(2)
    # Starts before 08:00
    res_early = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "07:30",
            "end_time": "08:30",
            "purpose": "Too early",
        },
    )
    assert res_early.status_code == 422

    # Ends after 20:00
    res_late = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "19:30",
            "end_time": "20:30",
            "purpose": "Too late",
        },
    )
    assert res_late.status_code == 422


def test_booking_non_30_minute_mark_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(2)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "09:15",
            "end_time": "10:15",
            "purpose": "Non-30 min interval",
        },
    )
    assert response.status_code == 422


def test_booking_end_time_before_or_equal_start_time_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(2)
    # End before start
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "14:00",
            "end_time": "11:00",
            "purpose": "Invalid backwards time",
        },
    )
    assert res1.status_code == 422

    # End equal start (0 duration)
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "10:00",
            "purpose": "Zero duration",
        },
    )
    assert res2.status_code == 422


def test_booking_duration_constraints_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(2)
    # Exceeding 3 hours (3 hours 30 mins)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "13:30",
            "purpose": "Exceeds 3 hours",
        },
    )
    assert response.status_code == 422


def test_booking_in_the_past_returns_422(client, auth_headers, test_room):
    past_date = get_past_date(2)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": past_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Past booking",
        },
    )
    assert response.status_code == 422


def test_booking_overlap_returns_409_with_slot_message(client, auth_headers, test_room):
    future_date = get_future_date(4)
    # 1. First booking: 10:00 - 11:30
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:30",
            "purpose": "Initial session",
        },
    )
    assert res1.status_code == 201

    # 2. Overlapping attempt (11:00 - 12:00)
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "11:00",
            "end_time": "12:00",
            "purpose": "Overlapping session",
        },
    )
    assert res2.status_code == 409
    assert "Slot 10:00-11:30 is already booked" in res2.json()["detail"]


def test_back_to_back_bookings_allowed(client, auth_headers, test_room):
    future_date = get_future_date(5)
    # 1. First booking: 10:00 - 11:00
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "First session",
        },
    )
    assert res1.status_code == 201

    # 2. Back-to-back after: 11:00 - 12:00 (Allowed)
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "11:00",
            "end_time": "12:00",
            "purpose": "Back-to-back after",
        },
    )
    assert res2.status_code == 201

    # 3. Back-to-back before: 09:00 - 10:00 (Allowed)
    res3 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "09:00",
            "end_time": "10:00",
            "purpose": "Back-to-back before",
        },
    )
    assert res3.status_code == 201


def test_bookings_sorted_by_real_time(client, auth_headers, test_room):
    future_date = get_future_date(6)
    # Create booking for 10:30 - 11:30 first
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:30",
            "end_time": "11:30",
            "purpose": "Later session",
        },
    )
    assert res1.status_code == 201

    # Create booking for 09:00 - 10:00 second (using "9:00")
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "9:00",
            "end_time": "10:00",
            "purpose": "Earlier session",
        },
    )
    assert res2.status_code == 201

    # Query room bookings for that date
    res_list = client.get(f"/rooms/{test_room.id}/bookings?date={future_date}", headers=auth_headers)
    assert res_list.status_code == 200
    bookings = res_list.json()
    assert len(bookings) == 2
    # Verify real-time sort: "09:00" must come before "10:30"
    assert bookings[0]["start_time"] == "09:00"
    assert bookings[1]["start_time"] == "10:30"


def test_get_my_bookings_shows_only_mine(client, auth_headers, test_user, test_room, db_session):
    future_date1 = get_future_date(7)
    future_date2 = get_future_date(8)

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
            "date": future_date1,
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
            "date": future_date2,
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
