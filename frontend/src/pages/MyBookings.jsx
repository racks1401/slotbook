import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

function timeToMinutes(tStr) {
  if (!tStr) return 0;
  const parts = tStr.split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

function getNowIndia() {
  const now = new Date();
  const dateStr = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);

  const timeParts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(now);

  return { dateStr, timeStr: timeParts };
}

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [roomsMap, setRoomsMap] = useState({});
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [cancellingId, setCancellingId] = useState(null);
  const navigate = useNavigate();

  const loadData = useCallback(() => {
    setLoading(true);
    setError('');

    Promise.all([
      apiFetch('/bookings/mine'),
      apiFetch('/rooms?include_inactive=true').catch(() => []),
      apiFetch('/auth/me').catch(() => null),
    ])
      .then(([bookingsData, roomsData, userData]) => {
        setBookings(bookingsData || []);
        setCurrentUser(userData);
        const map = {};
        if (Array.isArray(roomsData)) {
          roomsData.forEach((r) => {
            map[r.id] = r.name;
          });
        }
        setRoomsMap(map);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load your bookings.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }
    loadData();
  }, [navigate, loadData]);

  // Sort bookings by real time: newest date first, then chronological start time
  const sortedBookings = useMemo(() => {
    return [...bookings].sort((a, b) => {
      if (a.date !== b.date) {
        return b.date.localeCompare(a.date);
      }
      return timeToMinutes(a.start_time) - timeToMinutes(b.start_time);
    });
  }, [bookings]);

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) {
      return;
    }

    setCancellingId(bookingId);
    setError('');
    setActionSuccess('');

    try {
      await apiFetch(`/bookings/${bookingId}/cancel`, {
        method: 'POST',
      });
      setActionSuccess('Booking cancelled successfully.');
      loadData();
    } catch (err) {
      setError(err.message || 'Failed to cancel booking.');
    } finally {
      setCancellingId(null);
    }
  };

  const isCancellable = (booking) => {
    if (booking.status !== 'confirmed' && booking.status !== 'pending') {
      return false;
    }
    if (currentUser && currentUser.role === 'admin') {
      return true;
    }
    // Student can only cancel before start time (in India time)
    const { dateStr, timeStr } = getNowIndia();
    if (booking.date > dateStr) {
      return true;
    }
    if (booking.date === dateStr && booking.start_time > timeStr) {
      return true;
    }
    return false;
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

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading your bookings...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ maxWidth: '1000px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">My Bookings</h2>
          <p className="text-muted mb-0">View all your room reservations and cancellation history</p>
        </div>
      </div>

      {actionSuccess && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          {actionSuccess}
          <button type="button" className="btn-close" onClick={() => setActionSuccess('')} />
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {sortedBookings.length === 0 && !error ? (
        <div className="alert alert-light border py-4 text-center shadow-sm">
          <p className="mb-2 text-muted">No bookings yet.</p>
          <Link to="/" className="btn btn-primary btn-sm">
            Browse Rooms
          </Link>
        </div>
      ) : (
        <div className="card shadow-sm border-0">
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col">Room</th>
                    <th scope="col">Date</th>
                    <th scope="col">Time</th>
                    <th scope="col">Purpose</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="text-end">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedBookings.map((booking) => {
                    const roomName =
                      booking.room?.name || roomsMap[booking.room_id] || `Room #${booking.room_id}`;
                    const cancellable = isCancellable(booking);

                    return (
                      <tr key={booking.id}>
                        <td className="fw-semibold text-primary">{roomName}</td>
                        <td>{booking.date}</td>
                        <td>
                          {booking.start_time} - {booking.end_time}
                        </td>
                        <td>{booking.purpose}</td>
                        <td>{getStatusBadge(booking.status)}</td>
                        <td className="text-end">
                          {cancellable ? (
                            <button
                              className="btn btn-outline-danger btn-sm"
                              disabled={cancellingId === booking.id}
                              onClick={() => handleCancelBooking(booking.id)}
                            >
                              {cancellingId === booking.id ? 'Cancelling...' : 'Cancel'}
                            </button>
                          ) : (
                            <span className="text-muted small">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
