import { useEffect, useState } from 'react';
import api from '../api/client';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [enrollCourseId, setEnrollCourseId] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchUsers(); }, []);

  async function fetchUsers() {
    setLoading(true);
    const { data } = await api.get('/admin/users', { params: { search, limit: 100 } });
    setUsers(data);
    setLoading(false);
  }

  async function openUser(user) {
    setSelected(user);
    const [enr, crs] = await Promise.all([
      api.get(`/admin/users/${user.id}/enrollments`),
      api.get('/admin/courses'),
    ]);
    setEnrollments(enr.data);
    setCourses(crs.data);
  }

  async function toggleStatus(user) {
    const action = user.is_active ? 'deactivate' : 'activate';
    await api.patch(`/admin/users/${user.id}/${action}`);
    fetchUsers();
    if (selected?.id === user.id) setSelected({ ...user, is_active: !user.is_active });
  }

  async function enrollUser() {
    if (!enrollCourseId) return;
    await api.post(`/admin/users/${selected.id}/enrollments`, { course_id: enrollCourseId });
    const { data } = await api.get(`/admin/users/${selected.id}/enrollments`);
    setEnrollments(data);
    setEnrollCourseId('');
  }

  async function removeEnrollment(courseId) {
    await api.delete(`/admin/users/${selected.id}/enrollments/${courseId}`);
    setEnrollments(prev => prev.filter(e => e.course_id !== courseId));
  }

  const enrolledIds = new Set(enrollments.map(e => e.course_id));
  const availableCourses = courses.filter(c => !enrolledIds.has(c.id));

  return (
    <div className="admin-layout">
      <div className="admin-header">
        <h1>User Administration</h1>
        <div className="search-row">
          <input
            className="search-input"
            placeholder="Search by name or email…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchUsers()}
          />
          <button className="btn-primary" onClick={fetchUsers}>Search</button>
        </div>
      </div>

      <div className="admin-content">
        {/* User Table */}
        <div className="user-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="td-center">Loading…</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className={selected?.id === u.id ? 'row-selected' : ''} onClick={() => openUser(u)}>
                  <td>{u.full_name || '—'}</td>
                  <td>{u.email}</td>
                  <td><span className={`badge badge-${u.role}`}>{u.role}</span></td>
                  <td>
                    <span className={`badge ${u.is_active ? 'badge-active' : 'badge-inactive'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    <button
                      className={`btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`}
                      onClick={() => toggleStatus(u)}
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* User Detail Drawer */}
        {selected && (
          <div className="user-drawer">
            <div className="drawer-header">
              <div className="drawer-avatar">
                {selected.avatar_url
                  ? <img src={selected.avatar_url} alt="avatar" />
                  : <span>{selected.full_name?.[0] || '?'}</span>}
              </div>
              <div>
                <h3>{selected.full_name || selected.email}</h3>
                <p>{selected.email}</p>
                <span className={`badge ${selected.is_active ? 'badge-active' : 'badge-inactive'}`}>
                  {selected.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <button className="btn-close" onClick={() => setSelected(null)}>✕</button>
            </div>

            <div className="drawer-section">
              <h4>Course Enrollments</h4>
              {enrollments.length === 0
                ? <p className="empty-text">No active enrollments.</p>
                : enrollments.map(e => {
                    const course = courses.find(c => c.id === e.course_id);
                    return (
                      <div key={e.id} className="enrollment-row">
                        <span>{course?.title || e.course_id}</span>
                        <button className="btn-sm btn-danger" onClick={() => removeEnrollment(e.course_id)}>
                          Remove
                        </button>
                      </div>
                    );
                  })
              }
            </div>

            <div className="drawer-section">
              <h4>Enroll in a Course</h4>
              <div className="enroll-row">
                <select
                  className="select-input"
                  value={enrollCourseId}
                  onChange={e => setEnrollCourseId(e.target.value)}
                >
                  <option value="">Select a course…</option>
                  {availableCourses.map(c => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
                <button className="btn-primary" onClick={enrollUser}>Enroll</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
