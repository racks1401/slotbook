import React, { useEffect, useState, useCallback, useMemo } from 'react';
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

function getMaxDateIndia() {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(d);
}

function timeToMinutes(tStr) {
  if (!tStr) return 0;
  const parts = tStr.split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

// Generate 30-minute slots between 08:00 and 20:00
const TIME_SLOTS = [];
for (let h = 8; h <= 20; h++) {
  const hh = String(h).padStart(2, '0');
  TIME_SLOTS.push(`${hh}:00`);
  if (h < 20) {
    TIME_SLOTS.push(`${hh}:30`);
  }
}
const START_TIME_OPTIONS = TIME_SLOTS.slice(0, -1); // 08:00 to 19:30
const END_TIME_OPTIONS = TIME_SLOTS.slice(1); // 08:30 to 20:00

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
  const [repeatWeekly, setRepeatWeekly] = useState(false);
  const [repeatWeeks, setRepeatWeeks] = useState(2);
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
          setBookings(data || []);
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

  // Sort bookings by real time
  const sortedBookings = useMemo(() => {
    return [...bookings].sort((a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time));
  }, [bookings]);

  // Handle booking form submission
  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    setBookingError('');
    setBookingSuccess('');
    setSubmitting(true);

    try {
      const payload = {
        room_id: Number(id),
        date: selectedDate,
        start_time: startTime,
        end_time: endTime,
        purpose: purpose,
      };

      if (repeatWeekly) {
        payload.repeat_weeks = Number(repeatWeeks);
      }

      await apiFetch('/bookings', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (room && room.capacity >= 60) {
        setBookingSuccess(
          'Booking submitted successfully! Because this room has a capacity of 60+, it is pending admin approval.'
        );
      } else if (repeatWeekly) {
        setBookingSuccess(`Successfully reserved slots for ${repeatWeeks} consecutive weeks!`);
      } else {
        setBookingSuccess('Booking confirmed successfully!');
      }

      setStartTime('');
      setEndTime('');
      setPurpose('');
      setRepeatWeekly(false);
      setRepeatWeeks(2);
      loadBookings(selectedDate);
    } catch (err) {
      setBookingError(err.message || 'Failed to create booking.');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'confirmed':
        return <span className="badge bg-success">Confirmed</span>;
      case 'pending':
        return <span className="badge bg-warning text-dark">Pending</span>;
      case 'cancelled':
        return <span className="badge bg-secondary">Cancelled</span>;
      case 'rejected':
        return <span className="badge bg-danger">Rejected</span>;
      default:
        return <span className="badge bg-light text-dark">{status}</span>;
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
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h2 className="card-title fw-bold text-primary mb-2">{room.name}</h2>
                <div className="d-flex flex-wrap gap-3 text-muted">
                  <span>
                    <strong>Building:</strong> {room.building}
                  </span>
                  <span>•</span>
                  <span>
                    <strong>Capacity:</strong> {room.capacity} seats
                  </span>
                  <span>•</span>
                  <span>
                    <strong>Hours:</strong> 08:00 - 20:00
                  </span>
                </div>
              </div>
              {room.capacity >= 60 && (
                <span className="badge bg-warning text-dark fs-6 px-3 py-2">
                  Approval Required (60+ seats)
                </span>
              )}
            </div>

            {room.capacity >= 60 && (
              <div className="alert alert-warning mt-3 mb-0 py-2 small" role="alert">
                <strong>Notice:</strong> This room has a capacity of {room.capacity} seats. New bookings start as <em>pending</em> and require admin approval before being confirmed.
              </div>
            )}
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
                min={getTodayDateIndia()}
                max={getMaxDateIndia()}
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
          ) : sortedBookings.length === 0 ? (
            <div className="alert alert-light border text-muted py-3 text-center mb-0">
              No active bookings scheduled for this date.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col" style={{ width: '25%' }}>
                      Time Slot
                    </th>
                    <th scope="col">Purpose</th>
                    <th scope="col" style={{ width: '15%' }}>
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedBookings.map((b) => (
                    <tr key={b.id}>
                      <td className="fw-semibold text-primary">
                        {b.start_time} - {b.end_time}
                      </td>
                      <td>{b.purpose}</td>
                      <td>{getStatusBadge(b.status)}</td>
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
                  Start Time (30-min steps, 08:00 - 19:30)
                </label>
                <select
                  id="startTime"
                  className="form-select"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  required
                >
                  <option value="">Select start time</option>
                  {START_TIME_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold" htmlFor="endTime">
                  End Time (30-min steps, 08:30 - 20:00)
                </label>
                <select
                  id="endTime"
                  className="form-select"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  required
                >
                  <option value="">Select end time</option>
                  {END_TIME_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mb-3">
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

            {/* Recurring weekly booking option */}
            <div className="card bg-light border-0 p-3 mb-4">
              <div className="form-check mb-2">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="repeatWeeklyCheckbox"
                  checked={repeatWeekly}
                  onChange={(e) => setRepeatWeekly(e.target.checked)}
                />
                <label className="form-check-label fw-semibold" htmlFor="repeatWeeklyCheckbox">
                  Repeat weekly
                </label>
              </div>

              {repeatWeekly && (
                <div className="row align-items-center g-2 mt-1">
                  <div className="col-auto">
                    <label htmlFor="repeatWeeksSelect" className="col-form-label text-muted small">
                      Number of weeks:
                    </label>
                  </div>
                  <div className="col-auto">
                    <select
                      id="repeatWeeksSelect"
                      className="form-select form-select-sm"
                      value={repeatWeeks}
                      onChange={(e) => setRepeatWeeks(e.target.value)}
                    >
                      {[2, 3, 4, 5, 6, 7, 8].map((n) => (
                        <option key={n} value={n}>
                          {n} weeks
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-12 text-muted small">
                    Every week at the same time starting on {selectedDate}. If any date has a conflict, nothing will be booked.
                  </div>
                </div>
              )}
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
