import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [roomsMap, setRoomsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }

    setLoading(true);
    setError('');

    Promise.all([
      apiFetch('/bookings/mine'),
      apiFetch('/rooms').catch(() => []),
    ])
      .then(([bookingsData, roomsData]) => {
        setBookings(bookingsData || []);
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
  }, [navigate]);

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
    <div className="container mt-4" style={{ maxWidth: '950px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">My Bookings</h2>
          <p className="text-muted mb-0">View all your room reservations</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {bookings.length === 0 && !error ? (
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
                    <th scope="col">Start Time</th>
                    <th scope="col">End Time</th>
                    <th scope="col">Purpose</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.map((booking) => {
                    const roomName =
                      booking.room?.name || roomsMap[booking.room_id] || `Room #${booking.room_id}`;
                    return (
                      <tr key={booking.id}>
                        <td className="fw-semibold text-primary">{roomName}</td>
                        <td>{booking.date}</td>
                        <td>{booking.start_time}</td>
                        <td>{booking.end_time}</td>
                        <td>{booking.purpose}</td>
                        <td>{booking.status}</td>
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
