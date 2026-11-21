import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

export default function AdminApprovals() {
  const [pendingBookings, setPendingBookings] = useState([]);
  const [roomsMap, setRoomsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [actionId, setActionId] = useState(null);
  const navigate = useNavigate();

  const loadPending = useCallback(() => {
    setLoading(true);
    setError('');

    Promise.all([
      apiFetch('/bookings/pending'),
      apiFetch('/rooms?include_inactive=true').catch(() => []),
      apiFetch('/auth/me').catch(() => null),
    ])
      .then(([pendingData, roomsData, userData]) => {
        if (!userData || userData.role !== 'admin') {
          navigate('/');
          return;
        }
        setPendingBookings(pendingData || []);
        const map = {};
        if (Array.isArray(roomsData)) {
          roomsData.forEach((r) => {
            map[r.id] = r.name;
          });
        }
        setRoomsMap(map);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load pending bookings.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [navigate]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }
    loadPending();
  }, [navigate, loadPending]);

  const handleApprove = async (bookingId) => {
    setActionId(bookingId);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch(`/bookings/${bookingId}/approve`, {
        method: 'POST',
      });
      setSuccessMsg('Booking approved successfully!');
      loadPending();
    } catch (err) {
      setError(err.message || 'Failed to approve booking.');
    } finally {
      setActionId(null);
    }
  };

  const handleReject = async (bookingId) => {
    if (!window.confirm('Are you sure you want to reject this booking?')) {
      return;
    }

    setActionId(bookingId);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch(`/bookings/${bookingId}/reject`, {
        method: 'POST',
      });
      setSuccessMsg('Booking rejected.');
      loadPending();
    } catch (err) {
      setError(err.message || 'Failed to reject booking.');
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading pending approvals...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ maxWidth: '950px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">Booking Approvals</h2>
          <p className="text-muted mb-0">
            Review and approve or reject reservation requests for large capacity rooms (60+ seats)
          </p>
        </div>
        <span className="badge bg-warning text-dark fs-6 px-3 py-2">
          {pendingBookings.length} Pending
        </span>
      </div>

      {successMsg && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          {successMsg}
          <button type="button" className="btn-close" onClick={() => setSuccessMsg('')} />
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {pendingBookings.length === 0 && !error ? (
        <div className="alert alert-light border py-5 text-center shadow-sm">
          <h5 className="text-muted mb-2">No pending booking requests</h5>
          <p className="text-muted small mb-0">
            All reservation requests requiring approval have been processed.
          </p>
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
                    <th scope="col">Requested By</th>
                    <th scope="col" className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingBookings.map((b) => {
                    const roomName =
                      b.room?.name || roomsMap[b.room_id] || `Room #${b.room_id}`;
                    const userName = b.user?.name ? `${b.user.name} (${b.user.email})` : `User #${b.user_id}`;

                    return (
                      <tr key={b.id}>
                        <td className="fw-semibold text-primary">{roomName}</td>
                        <td>{b.date}</td>
                        <td>
                          {b.start_time} - {b.end_time}
                        </td>
                        <td>{b.purpose}</td>
                        <td className="small text-muted">{userName}</td>
                        <td className="text-end">
                          <div className="btn-group btn-group-sm">
                            <button
                              className="btn btn-success"
                              disabled={actionId === b.id}
                              onClick={() => handleApprove(b.id)}
                            >
                              {actionId === b.id ? 'Processing...' : 'Approve'}
                            </button>
                            <button
                              className="btn btn-outline-danger"
                              disabled={actionId === b.id}
                              onClick={() => handleReject(b.id)}
                            >
                              Reject
                            </button>
                          </div>
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
