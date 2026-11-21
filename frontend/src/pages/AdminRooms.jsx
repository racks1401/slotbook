import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch, getToken } from '../api';

export default function AdminRooms() {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const navigate = useNavigate();

  // Add room form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newBuilding, setNewBuilding] = useState('');
  const [newCapacity, setNewCapacity] = useState('');
  const [adding, setAdding] = useState(false);

  // Edit room form state
  const [editingRoom, setEditingRoom] = useState(null);
  const [editName, setEditName] = useState('');
  const [editBuilding, setEditBuilding] = useState('');
  const [editCapacity, setEditCapacity] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Action status
  const [actionId, setActionId] = useState(null);

  const loadRooms = useCallback(() => {
    setLoading(true);
    setError('');

    Promise.all([
      apiFetch('/rooms?include_inactive=true'),
      apiFetch('/auth/me').catch(() => null),
    ])
      .then(([roomsData, userData]) => {
        if (!userData || userData.role !== 'admin') {
          navigate('/');
          return;
        }
        setRooms(roomsData || []);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load rooms.');
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
    loadRooms();
  }, [navigate, loadRooms]);

  const handleAddRoom = async (e) => {
    e.preventDefault();
    setAdding(true);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch('/rooms', {
        method: 'POST',
        body: JSON.stringify({
          name: newName.trim(),
          building: newBuilding.trim(),
          capacity: Number(newCapacity),
        }),
      });

      setSuccessMsg('Room created successfully!');
      setNewName('');
      setNewBuilding('');
      setNewCapacity('');
      setShowAddForm(false);
      loadRooms();
    } catch (err) {
      setError(err.message || 'Failed to create room.');
    } finally {
      setAdding(false);
    }
  };

  const startEdit = (room) => {
    setEditingRoom(room);
    setEditName(room.name);
    setEditBuilding(room.building);
    setEditCapacity(String(room.capacity));
    setError('');
    setSuccessMsg('');
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingRoom) return;
    setSavingEdit(true);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch(`/rooms/${editingRoom.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName.trim(),
          building: editBuilding.trim(),
          capacity: Number(editCapacity),
        }),
      });

      setSuccessMsg('Room updated successfully!');
      setEditingRoom(null);
      loadRooms();
    } catch (err) {
      setError(err.message || 'Failed to update room.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleCloseRoom = async (roomId) => {
    if (!window.confirm('Are you sure you want to close this room? It will no longer be available for booking.')) {
      return;
    }

    setActionId(roomId);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch(`/rooms/${roomId}/close`, {
        method: 'POST',
      });
      setSuccessMsg('Room closed successfully.');
      loadRooms();
    } catch (err) {
      setError(err.message || 'Failed to close room.');
    } finally {
      setActionId(null);
    }
  };

  const handleReopenRoom = async (roomId) => {
    setActionId(roomId);
    setError('');
    setSuccessMsg('');

    try {
      await apiFetch(`/rooms/${roomId}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: true }),
      });
      setSuccessMsg('Room reopened successfully.');
      loadRooms();
    } catch (err) {
      setError(err.message || 'Failed to reopen room.');
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading rooms...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ maxWidth: '950px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">Room Management</h2>
          <p className="text-muted mb-0">Add, edit, and close campus rooms</p>
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? 'Cancel' : '+ Add New Room'}
        </button>
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

      {/* Add Room Form Card */}
      {showAddForm && (
        <div className="card shadow-sm border-0 mb-4 bg-light">
          <div className="card-body p-4">
            <h5 className="fw-bold mb-3">Add New Room</h5>
            <form onSubmit={handleAddRoom}>
              <div className="row g-3">
                <div className="col-md-4">
                  <label className="form-label small fw-semibold" htmlFor="newRoomName">
                    Room Name
                  </label>
                  <input
                    id="newRoomName"
                    type="text"
                    className="form-control form-control-sm"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Newton Physics Lab"
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label small fw-semibold" htmlFor="newRoomBuilding">
                    Building
                  </label>
                  <input
                    id="newRoomBuilding"
                    type="text"
                    className="form-control form-control-sm"
                    value={newBuilding}
                    onChange={(e) => setNewBuilding(e.target.value)}
                    placeholder="e.g. Science Wing"
                    required
                  />
                </div>
                <div className="col-md-2">
                  <label className="form-label small fw-semibold" htmlFor="newRoomCapacity">
                    Capacity
                  </label>
                  <input
                    id="newRoomCapacity"
                    type="number"
                    min="1"
                    className="form-control form-control-sm"
                    value={newCapacity}
                    onChange={(e) => setNewCapacity(e.target.value)}
                    placeholder="e.g. 50"
                    required
                  />
                </div>
                <div className="col-md-2 d-flex align-items-end">
                  <button type="submit" className="btn btn-success btn-sm w-100" disabled={adding}>
                    {adding ? 'Saving...' : 'Create'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Room Modal / Section */}
      {editingRoom && (
        <div className="card shadow-sm border-primary mb-4">
          <div className="card-body p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold text-primary mb-0">Edit Room: {editingRoom.name}</h5>
              <button
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setEditingRoom(null)}
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSaveEdit}>
              <div className="row g-3">
                <div className="col-md-4">
                  <label className="form-label small fw-semibold">Name</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label small fw-semibold">Building</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={editBuilding}
                    onChange={(e) => setEditBuilding(e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-2">
                  <label className="form-label small fw-semibold">Capacity</label>
                  <input
                    type="number"
                    min="1"
                    className="form-control form-control-sm"
                    value={editCapacity}
                    onChange={(e) => setEditCapacity(e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-2 d-flex align-items-end">
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm w-100"
                    disabled={savingEdit}
                  >
                    {savingEdit ? 'Updating...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rooms List Table */}
      <div className="card shadow-sm border-0">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Building</th>
                  <th scope="col">Capacity</th>
                  <th scope="col">Status</th>
                  <th scope="col" className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rooms.map((r) => (
                  <tr key={r.id}>
                    <td className="fw-semibold text-primary">{r.name}</td>
                    <td>{r.building}</td>
                    <td>
                      {r.capacity} seats{' '}
                      {r.capacity >= 60 && (
                        <span className="badge bg-warning text-dark ms-1 small">
                          Approval required
                        </span>
                      )}
                    </td>
                    <td>
                      {r.is_active ? (
                        <span className="badge bg-success">Active</span>
                      ) : (
                        <span className="badge bg-secondary">Closed</span>
                      )}
                    </td>
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        <button
                          className="btn btn-outline-secondary"
                          onClick={() => startEdit(r)}
                        >
                          Edit
                        </button>
                        {r.is_active ? (
                          <button
                            className="btn btn-outline-danger"
                            disabled={actionId === r.id}
                            onClick={() => handleCloseRoom(r.id)}
                          >
                            {actionId === r.id ? 'Closing...' : 'Close Room'}
                          </button>
                        ) : (
                          <button
                            className="btn btn-outline-success"
                            disabled={actionId === r.id}
                            onClick={() => handleReopenRoom(r.id)}
                          >
                            Reopen
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
