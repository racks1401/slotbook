import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { clearToken, getToken } from '../api';

export default function Navbar({ onLogout }) {
  const navigate = useNavigate();
  const token = getToken();

  const handleLogout = () => {
    clearToken();
    if (onLogout) onLogout();
    navigate('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm mb-4">
      <div className="container">
        <Link className="navbar-brand fw-bold" to="/">
          SlotBook
        </Link>
        <div className="d-flex align-items-center">
          {token ? (
            <div className="d-flex align-items-center gap-3">
              <Link className="nav-link text-white" to="/">
                Rooms
              </Link>
              <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
                Logout
              </button>
            </div>
          ) : (
            <div className="navbar-nav flex-row gap-3">
              <Link className="nav-link text-white" to="/login">
                Login
              </Link>
              <Link className="nav-link text-white" to="/register">
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
