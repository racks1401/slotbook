import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

export default function Home() {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }

    apiFetch('/rooms')
      .then((data) => {
        setRooms(data);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [navigate]);

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">Available Rooms</h2>
          <p className="text-muted mb-0">Select a room to view bookings and reserve a slot</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {rooms.length === 0 && !error ? (
        <div className="alert alert-info">No active rooms found.</div>
      ) : (
        <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
          {rooms.map((room) => (
            <div key={room.id} className="col">
              <div className="card h-100 shadow-sm border-0">
                <div className="card-body d-flex flex-column">
                  <h5 className="card-title fw-bold text-primary">{room.name}</h5>
                  <p className="card-text text-muted mb-1">
                    <strong>Building:</strong> {room.building}
                  </p>
                  <p className="card-text text-muted mb-4">
                    <strong>Capacity:</strong> {room.capacity} seats
                  </p>
                  <div className="mt-auto">
                    <Link to={`/rooms/${room.id}`} className="btn btn-primary w-100">
                      View Bookings & Book
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
