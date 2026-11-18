import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

function getTodayDateIndia() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(new Date());
}

export default function RoomDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [room, setRoom] = useState(null);
  const [roomLoading, setRoomLoading] = useState(true);
  const [roomNotFound, setRoomNotFound] = useState(false);
  const [roomError, setRoomError] = useState('');

  const [selectedDate, setSelectedDate] = useState(getTodayDateIndia());
  const [bookings, setBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingsError, setBookingsError] = useState('');

  // Booking form state
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [purpose, setPurpose] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [bookingError, setBookingError] = useState('');
  const [bookingSuccess, setBookingSuccess] = useState('');

  // Load room details
  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }

    setRoomLoading(true);
    setRoomError('');
    setRoomNotFound(false);

    apiFetch(`/rooms/${id}`)
      .then((data) => {
        setRoom(data);
      })
      .catch((err) => {
        if (err.status === 404) {
          setRoomNotFound(true);
        } else {
          setRoomError(err.message || 'Failed to load room details.');
        }
      })
      .finally(() => {
        setRoomLoading(false);
      });
  }, [id, navigate]);

  // Load bookings for selected date
  const loadBookings = useCallback(
    (date) => {
      if (!id || !date) return;
      setBookingsLoading(true);
      setBookingsError('');

      apiFetch(`/rooms/${id}/bookings?date=${date}`)
        .then((data) => {
          setBookings(data);
        })
        .catch((err) => {
          setBookingsError(err.message || 'Failed to load bookings for this date.');
        })
        .finally(() => {
          setBookingsLoading(false);
        });
    },
    [id]
  );

  useEffect(() => {
    const token = getToken();
    if (token && id && !roomNotFound) {
      loadBookings(selectedDate);
    }
  }, [id, selectedDate, roomNotFound, loadBookings]);

  // Handle booking form submission
  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    setBookingError('');
    setBookingSuccess('');
    setSubmitting(true);

    try {
      await apiFetch('/bookings', {
        method: 'POST',
        body: JSON.stringify({
          room_id: Number(id),
          date: selectedDate,
          start_time: startTime,
          end_time: endTime,
          purpose: purpose,
        }),
      });

      setBookingSuccess('Booking confirmed successfully!');
      setStartTime('');
      setEndTime('');
      setPurpose('');
      loadBookings(selectedDate);
    } catch (err) {
      setBookingError(err.message || 'Failed to create booking.');
    } finally {
      setSubmitting(false);
    }
  };

  if (roomLoading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading room...</span>
        </div>
      </div>
    );
  }

  if (roomNotFound) {
    return (
      <div className="container mt-5" style={{ maxWidth: '600px' }}>
        <div className="alert alert-warning py-4 text-center shadow-sm" role="alert">
          <h4 className="alert-heading fw-bold mb-2">Room not found</h4>
          <p className="mb-4 text-muted">The room you are looking for does not exist or has been removed.</p>
          <Link to="/" className="btn btn-primary">
            Back to Rooms
          </Link>
        </div>
      </div>
    );
  }

  if (roomError) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger" role="alert">
          {roomError}
        </div>
        <Link to="/" className="btn btn-outline-secondary">
          &larr; Back to Rooms
        </Link>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ maxWidth: '850px' }}>
      <div className="mb-3">
        <Link to="/" className="btn btn-outline-secondary btn-sm">
          &larr; Back to Rooms
        </Link>
      </div>

      {/* Room Header Card */}
      {room && (
        <div className="card shadow-sm border-0 mb-4">
          <div className="card-body p-4">
            <h2 className="card-title fw-bold text-primary mb-2">{room.name}</h2>
            <div className="d-flex flex-wrap gap-3 text-muted">
              <span>
                <strong>Building:</strong> {room.building}
              </span>
              <span>•</span>
              <span>
                <strong>Capacity:</strong> {room.capacity} seats
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Date Picker & Bookings Section */}
      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body p-4">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
            <h4 className="fw-bold mb-0">Bookings for Date</h4>
            <div className="d-flex align-items-center gap-2">
              <label htmlFor="booking-date" className="form-label mb-0 fw-semibold">
                Date:
              </label>
              <input
                id="booking-date"
                type="date"
                className="form-control"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>
          </div>

          {bookingsError && (
            <div className="alert alert-danger" role="alert">
              {bookingsError}
            </div>
          )}

          {bookingsLoading ? (
            <div className="text-center py-4">
              <div className="spinner-border spinner-border-sm text-primary" role="status">
                <span className="visually-hidden">Loading bookings...</span>
              </div>
            </div>
          ) : bookings.length === 0 ? (
            <div className="alert alert-light border text-muted py-3 text-center mb-0">
              No bookings scheduled for this date.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col" style={{ width: '22%' }}>
                      Time Slot
                    </th>
                    <th scope="col">Purpose</th>
                    <th scope="col" style={{ width: '15%' }}>
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.map((b) => (
                    <tr key={b.id}>
                      <td className="fw-semibold text-primary">
                        {b.start_time} - {b.end_time}
                      </td>
                      <td>{b.purpose}</td>
                      <td>
                        <span className="badge bg-success-subtle text-success border border-success-subtle">
                          {b.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Booking Form Section */}
      <div className="card shadow-sm border-0 mb-5">
        <div className="card-body p-4">
          <h4 className="fw-bold mb-3">Book This Room</h4>

          {bookingSuccess && (
            <div className="alert alert-success" role="alert">
              {bookingSuccess}
            </div>
          )}

          {bookingError && (
            <div className="alert alert-danger" role="alert">
              {bookingError}
            </div>
          )}

          <form onSubmit={handleBookingSubmit}>
            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <label className="form-label fw-semibold" htmlFor="startTime">
                  Start Time
                </label>
                <input
                  id="startTime"
                  type="time"
                  className="form-control"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold" htmlFor="endTime">
                  End Time
                </label>
                <input
                  id="endTime"
                  type="time"
                  className="form-control"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="form-label fw-semibold" htmlFor="purpose">
                Purpose (max 200 characters)
              </label>
              <input
                id="purpose"
                type="text"
                maxLength={200}
                className="form-control"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Algorithms project group study"
                required
              />
              <div className="form-text text-muted">{purpose.length}/200 characters</div>
            </div>

            <button type="submit" className="btn btn-primary px-4 py-2" disabled={submitting}>
              {submitting ? 'Confirming...' : 'Reserve Room'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
