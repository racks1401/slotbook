import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import RoomDetail from './pages/RoomDetail';
import MyBookings from './pages/MyBookings';
import Login from './pages/Login';
import Register from './pages/Register';

export default function App() {
  const [authVersion, setAuthVersion] = useState(0);

  const handleAuthChange = () => {
    setAuthVersion((v) => v + 1);
  };

  return (
    <div>
      <Navbar key={authVersion} onLogout={handleAuthChange} />
      <main>
        <Routes>
          <Route path="/" element={<Home key={authVersion} />} />
          <Route path="/rooms/:id" element={<RoomDetail key={authVersion} />} />
          <Route path="/my-bookings" element={<MyBookings key={authVersion} />} />
          <Route path="/login" element={<Login onLoginSuccess={handleAuthChange} />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
