import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
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
    <nav className="navbar navbar-expand navbar-dark bg-primary shadow-sm mb-4">
      <div className="container">
        <Link className="navbar-brand fw-bold" to="/">
          SlotBook
        </Link>
        <div className="d-flex align-items-center justify-content-between flex-grow-1 ms-3">
          {token ? (
            <>
              <div className="navbar-nav me-auto">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                  }
                >
                  Rooms
                </NavLink>
                <NavLink
                  to="/my-bookings"
                  className={({ isActive }) =>
                    `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                  }
                >
                  My Bookings
                </NavLink>
              </div>
              <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <div className="navbar-nav ms-auto">
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                }
              >
                Login
              </NavLink>
              <NavLink
                to="/register"
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                }
              >
                Register
              </NavLink>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
