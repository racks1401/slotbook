from datetime import datetime, timedelta, timezone
from app.auth import hash_password, create_access_token
from app.models import Booking, Room, User

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


def test_booking_more_than_14_days_ahead_returns_422(client, auth_headers, test_room):
    too_far = get_future_date(15)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": too_far,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Too far ahead",
        },
    )
    assert response.status_code == 422
    assert "14 days" in response.json()["detail"]


def test_booking_within_14_days_succeeds(client, auth_headers, test_room):
    within_limit = get_future_date(14)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": within_limit,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Day 14 booking",
        },
    )
    assert response.status_code == 201


def test_student_daily_4_hour_limit_exceeded_returns_422(client, auth_headers, test_room):
    future_date = get_future_date(3)
    # 1. Book 3 hours (180 mins)
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "09:00",
            "end_time": "12:00",
            "purpose": "3 hour morning block",
        },
    )
    assert res1.status_code == 201

    # 2. Book 1 hour (60 mins) -> total 4 hours (240 mins) exactly allowed
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "13:00",
            "end_time": "14:00",
            "purpose": "1 hour afternoon block",
        },
    )
    assert res2.status_code == 201

    # 3. Attempt another 30 mins -> total 4.5 hours -> rejected 422
    res3 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "15:00",
            "end_time": "15:30",
            "purpose": "Extra 30 mins exceeding limit",
        },
    )
    assert res3.status_code == 422
    assert "Daily booking limit" in res3.json()["detail"]


def test_admin_exempt_from_daily_limit(client, admin_headers, test_room):
    future_date = get_future_date(4)
    # Admin books 3 hours
    res1 = client.post(
        "/bookings",
        headers=admin_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "09:00",
            "end_time": "12:00",
            "purpose": "Admin morning block",
        },
    )
    assert res1.status_code == 201

    # Admin books another 2.5 hours -> total 5.5 hours -> allowed!
    res2 = client.post(
        "/bookings",
        headers=admin_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "13:00",
            "end_time": "15:30",
            "purpose": "Admin afternoon block",
        },
    )
    assert res2.status_code == 201


def test_daily_limit_spans_multiple_rooms(client, auth_headers, test_room, db_session):
    room2 = Room(name="Secondary Room", building="Main Block", capacity=25, is_active=True)
    db_session.add(room2)
    db_session.commit()
    db_session.refresh(room2)

    future_date = get_future_date(5)
    # Book 2.5 hours in room 1
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "09:00",
            "end_time": "11:30",
            "purpose": "Lab work",
        },
    )
    assert res1.status_code == 201

    # Try booking 2 hours in room 2 (2.5 + 2 = 4.5 hours) -> rejected
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": room2.id,
            "date": future_date,
            "start_time": "12:00",
            "end_time": "14:00",
            "purpose": "Seminar in other room",
        },
    )
    assert res2.status_code == 422
    assert "Daily booking limit" in res2.json()["detail"]


def test_capacity_60_or_more_starts_as_pending(client, auth_headers, large_room):
    future_date = get_future_date(3)
    response = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": large_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:30",
            "purpose": "Large guest lecture",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_admin_can_approve_pending_booking(client, auth_headers, admin_headers, large_room):
    future_date = get_future_date(3)
    # 1. Student requests large room
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": large_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Department seminar",
        },
    )
    assert res.status_code == 201
    booking_id = res.json()["id"]
    assert res.json()["status"] == "pending"

    # 2. Check pending list
    res_pending = client.get("/bookings/pending", headers=admin_headers)
    assert res_pending.status_code == 200
    pending_ids = [b["id"] for b in res_pending.json()]
    assert booking_id in pending_ids

    # 3. Non-admin cannot approve
    res_forbidden = client.post(f"/bookings/{booking_id}/approve", headers=auth_headers)
    assert res_forbidden.status_code == 403

    # 4. Admin approves
    res_approve = client.post(f"/bookings/{booking_id}/approve", headers=admin_headers)
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "confirmed"


def test_admin_approval_checks_clashes_again(client, auth_headers, admin_headers, large_room, test_user, db_session):
    from app.models import Booking
    future_date = get_future_date(4)

    # Directly create two pending bookings for the same room and overlapping time
    b1 = Booking(
        room_id=large_room.id,
        user_id=test_user.id,
        date=future_date,
        start_time="10:00",
        end_time="11:30",
        purpose="Event A",
        status="pending",
    )
    b2 = Booking(
        room_id=large_room.id,
        user_id=test_user.id,
        date=future_date,
        start_time="11:00",
        end_time="12:00",
        purpose="Event B",
        status="pending",
    )
    db_session.add_all([b1, b2])
    db_session.commit()
    db_session.refresh(b1)
    db_session.refresh(b2)

    # Approve b1
    res1 = client.post(f"/bookings/{b1.id}/approve", headers=admin_headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "confirmed"

    # Approving b2 should detect clash with confirmed b1 and return 409
    res2 = client.post(f"/bookings/{b2.id}/approve", headers=admin_headers)
    assert res2.status_code == 409
    assert "Slot 10:00-11:30 is already booked" in res2.json()["detail"]


def test_admin_can_reject_pending_booking(client, auth_headers, admin_headers, large_room):
    future_date = get_future_date(3)
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": large_room.id,
            "date": future_date,
            "start_time": "14:00",
            "end_time": "15:00",
            "purpose": "Club meeting",
        },
    )
    booking_id = res.json()["id"]

    res_reject = client.post(f"/bookings/{booking_id}/reject", headers=admin_headers)
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "rejected"


def test_student_can_cancel_own_upcoming_booking(client, auth_headers, test_room):
    future_date = get_future_date(3)
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Review session",
        },
    )
    booking_id = res.json()["id"]

    res_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"


def test_cancelled_booking_frees_slot_for_new_booking(client, auth_headers, test_room):
    future_date = get_future_date(4)
    res1 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Initial session",
        },
    )
    booking_id = res1.json()["id"]

    # Cancel booking
    client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)

    # Re-book the same slot -> should succeed because slot is freed
    res2 = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "New session in freed slot",
        },
    )
    assert res2.status_code == 201


def test_student_cannot_cancel_another_user_booking(client, auth_headers, test_room, db_session):
    user2 = User(
        name="Student Two",
        email="student2@college.edu",
        password_hash=hash_password("pw2"),
        role="student",
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)
    user2_token = create_access_token(data={"sub": str(user2.id)})
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    future_date = get_future_date(3)
    res = client.post(
        "/bookings",
        headers=user2_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "User 2 reservation",
        },
    )
    booking_id = res.json()["id"]

    # User 1 attempts to cancel User 2's booking -> 403 Forbidden
    res_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)
    assert res_cancel.status_code == 403


def test_admin_can_cancel_any_booking(client, admin_headers, auth_headers, test_room):
    future_date = get_future_date(3)
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": future_date,
            "start_time": "14:00",
            "end_time": "15:00",
            "purpose": "Student reservation",
        },
    )
    booking_id = res.json()["id"]

    res_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=admin_headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"


def test_recurring_weekly_booking_success(client, auth_headers, test_room):
    start_date = get_future_date(1)
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": start_date,
            "start_time": "16:00",
            "end_time": "17:00",
            "purpose": "Weekly Study Group",
            "repeat_weeks": 3,
        },
    )
    assert res.status_code == 201
    bookings = res.json()
    assert isinstance(bookings, list)
    assert len(bookings) == 3
    dates = [b["date"] for b in bookings]
    expected_d0 = start_date
    expected_d1 = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    expected_d2 = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d")
    assert dates == [expected_d0, expected_d1, expected_d2]


def test_recurring_weekly_booking_all_or_nothing_on_clash(client, auth_headers, test_room):
    start_date = get_future_date(1)
    clash_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

    # Pre-book week 2's slot
    client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": clash_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Pre-existing session on week 2",
        },
    )

    # Attempt to book 3 recurring weeks at 10:00-11:00 -> week 2 will clash
    res = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": test_room.id,
            "date": start_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Recurring team sync",
            "repeat_weeks": 3,
        },
    )
    assert res.status_code == 409
    assert clash_date in res.json()["detail"]

    # Verify all-or-nothing: week 1 must NOT be booked
    res_w1 = client.get(f"/rooms/{test_room.id}/bookings?date={start_date}", headers=auth_headers)
    assert len(res_w1.json()) == 0


def test_admin_room_management_add_edit_close(client, admin_headers, auth_headers):
    # 1. Non-admin cannot add room
    res_forbid = client.post(
        "/rooms",
        headers=auth_headers,
        json={"name": "New Lab", "building": "Block C", "capacity": 20},
    )
    assert res_forbid.status_code == 403

    # 2. Admin adds room
    res_add = client.post(
        "/rooms",
        headers=admin_headers,
        json={"name": "Quantum Lab", "building": "Science Wing", "capacity": 25},
    )
    assert res_add.status_code == 201
    new_room = res_add.json()
    room_id = new_room["id"]
    assert new_room["name"] == "Quantum Lab"

    # 3. Admin edits room
    res_edit = client.put(
        f"/rooms/{room_id}",
        headers=admin_headers,
        json={"capacity": 30},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["capacity"] == 30

    # 4. Book room on future date
    future_date = get_future_date(2)
    res_book = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "room_id": room_id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Lab experiment",
        },
    )
    assert res_book.status_code == 201
    booking_id = res_book.json()["id"]

    # 5. Cannot close room with future bookings
    res_close_fail = client.post(f"/rooms/{room_id}/close", headers=admin_headers)
    assert res_close_fail.status_code == 400
    assert "Cannot close room with future confirmed or pending bookings" in res_close_fail.json()["detail"]

    # 6. Cancel the future booking
    client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)

    # 7. Now close the room -> succeeds
    res_close_ok = client.post(f"/rooms/{room_id}/close", headers=admin_headers)
    assert res_close_ok.status_code == 200
    assert res_close_ok.json()["is_active"] is False

    # 8. Check GET /rooms does not list inactive room by default
    res_rooms = client.get("/rooms", headers=auth_headers)
    ids = [r["id"] for r in res_rooms.json()]
    assert room_id not in ids

    # 9. GET /rooms?include_inactive=true lists it
    res_all_rooms = client.get("/rooms?include_inactive=true", headers=admin_headers)
    ids_all = [r["id"] for r in res_all_rooms.json()]
    assert room_id in ids_all
