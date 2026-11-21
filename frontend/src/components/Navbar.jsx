import React, { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { clearToken, getToken, apiFetch } from '../api';

export default function Navbar({ onLogout }) {
  const navigate = useNavigate();
  const token = getToken();
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      apiFetch('/auth/me')
        .then((userData) => setUser(userData))
        .catch(() => setUser(null));
    } else {
      setUser(null);
    }
  }, [token]);

  const handleLogout = () => {
    clearToken();
    setUser(null);
    if (onLogout) onLogout();
    navigate('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm mb-4">
      <div className="container">
        <Link className="navbar-brand fw-bold" to="/">
          SlotBook
        </Link>
        <div className="d-flex align-items-center justify-content-between flex-grow-1 ms-3">
          {token ? (
            <>
              <div className="navbar-nav me-auto d-flex flex-row gap-3">
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

                {user && user.role === 'admin' && (
                  <>
                    <NavLink
                      to="/admin/approvals"
                      className={({ isActive }) =>
                        `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                      }
                    >
                      Approvals
                    </NavLink>
                    <NavLink
                      to="/admin/rooms"
                      className={({ isActive }) =>
                        `nav-link ${isActive ? 'active fw-bold text-white' : 'text-white-50'}`
                      }
                    >
                      Manage Rooms
                    </NavLink>
                  </>
                )}
              </div>
              <div className="d-flex align-items-center gap-3">
                {user && (
                  <span className="text-white-50 small d-none d-md-inline">
                    {user.name}{' '}
                    {user.role === 'admin' && (
                      <span className="badge bg-warning text-dark ms-1">Admin</span>
                    )}
                  </span>
                )}
                <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
                  Logout
                </button>
              </div>
            </>
          ) : (
            <div className="navbar-nav ms-auto d-flex flex-row gap-3">
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
