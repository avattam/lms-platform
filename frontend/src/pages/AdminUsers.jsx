import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import pageConfig from './config.json';

const config = pageConfig.adminUsers;

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [enrollCourseId, setEnrollCourseId] = useState('');
  const [loading, setLoading] = useState(true);

  // Modal and Form states
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [formData, setFormData] = useState({ email: '', full_name: '', id_proof: '', role: 'student', is_active: true });
  const [formError, setFormError] = useState('');

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

  function openCreateModal() {
    setFormData({ email: '', full_name: '', id_proof: '', role: 'student', is_active: true });
    setFormError('');
    setModalMode('create');
    setModalOpen(true);
  }

  function openEditModal() {
    setFormData({
      email: selected.email,
      full_name: selected.full_name || '',
      id_proof: selected.id_proof || '',
      role: selected.role,
      is_active: selected.is_active,
    });
    setFormError('');
    setModalMode('edit');
    setModalOpen(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError('');
    try {
      if (modalMode === 'create') {
        const { data } = await api.post('/admin/users', formData);
        setUsers(prev => [data, ...prev]);
        setModalOpen(false);
      } else {
        const { data } = await api.patch(`/admin/users/${selected.id}`, formData);
        setUsers(prev => prev.map(u => u.id === data.id ? data : u));
        setSelected(data);
        setModalOpen(false);
      }
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred. Please try again.');
    }
  }

  async function deleteUser() {
    if (!window.confirm(`Are you sure you want to delete ${selected.full_name || selected.email}? This cannot be undone.`)) {
      return;
    }
    try {
      await api.delete(`/admin/users/${selected.id}`);
      setUsers(prev => prev.filter(u => u.id !== selected.id));
      setSelected(null);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete user.');
    }
  }

  const enrolledIds = new Set(enrollments.map(e => e.course_id));
  const availableCourses = courses.filter(c => !enrolledIds.has(c.id));

  return (
    <div className="admin-layout">
      <div className="admin-header">
        <h1>{config.header.title}</h1>
        <div className="search-row">
          <input
            className="search-input"
            placeholder={config.header.searchPlaceholder}
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchUsers()}
          />
          <button className="btn-primary" onClick={fetchUsers}>{config.header.searchButtonText}</button>
          <button className="btn-primary" onClick={openCreateModal}>{config.header.addUserButtonText}</button>
        </div>
        <Link to={config.header.backLink.to} className="btn-ghost">{config.header.backLink.text}</Link>
      </div>

      <div className="admin-content">
        {/* User Table */}
        <div className="user-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {config.userTable.columns.map(col => (
                  <th key={col.key}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={config.userTable.columns.length} className="td-center">{config.userTable.loadingText}</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className={selected?.id === u.id ? 'row-selected' : ''} onClick={() => openUser(u)}>
                  {config.userTable.columns.map(col => {
                    if (col.key === 'name') return <td key={col.key}>{u.full_name || '—'}</td>;
                    if (col.key === 'email') return <td key={col.key}>{u.email}</td>;
                    if (col.key === 'id_proof') return <td key={col.key} className="td-mono">{u.id_proof || '—'}</td>;
                    if (col.key === 'role') return <td key={col.key}><span className={`badge badge-${u.role}`}>{u.role}</span></td>;
                    if (col.key === 'status') return (
                      <td key={col.key}>
                        <span className={u.is_active ? config.userTable.badges.active.className : config.userTable.badges.inactive.className}>
                          {u.is_active ? config.userTable.badges.active.text : config.userTable.badges.inactive.text}
                        </span>
                      </td>
                    );
                    if (col.key === 'actions') return (
                      <td key={col.key} onClick={e => e.stopPropagation()}>
                        <button
                          className={`btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`}
                          onClick={() => toggleStatus(u)}
                        >
                          {u.is_active ? config.userTable.actions.deactivate : config.userTable.actions.activate}
                        </button>
                      </td>
                    );
                    return <td key={col.key}>{u[col.key] || '—'}</td>;
                  })}
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
                {selected.id_proof && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    ID Proof: {selected.id_proof}
                  </p>
                )}
                <span className={selected.is_active ? config.userTable.badges.active.className : config.userTable.badges.inactive.className}>
                  {selected.is_active ? config.userTable.badges.active.text : config.userTable.badges.inactive.text}
                </span>
              </div>
              <button className="btn-close" onClick={() => setSelected(null)}>✕</button>
            </div>

            <div className="drawer-section" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '1rem', display: 'flex', flexDirection: 'row', gap: '0.5rem' }}>
              <button className="btn-sm" onClick={openEditModal} style={{ flex: 1 }}>{config.modal.editTitle}</button>
              <button className="btn-sm btn-danger" onClick={deleteUser} style={{ flex: 1 }}>{config.selectedUserPanel.deleteUserButtonText}</button>
            </div>

            <div className="drawer-section">
              <h4>Course Enrollments</h4>
              {enrollments.length === 0
                ? <p className="empty-text">{config.selectedUserPanel.enrollments.emptyText}</p>
                : enrollments.map(e => {
                    const course = courses.find(c => c.id === e.course_id);
                    return (
                      <div key={e.id} className="enrollment-row">
                        <span>{course?.title || e.course_id}</span>
                        <button className="btn-sm btn-danger" onClick={() => removeEnrollment(e.course_id)}>
                          {config.selectedUserPanel.enrollments.removeButtonText}
                        </button>
                      </div>
                    );
                  })
              }
            </div>

            <div className="drawer-section">
              <h4>{config.selectedUserPanel.enrollForm.title}</h4>
              <div className="enroll-row">
                <select
                  className="select-input"
                  value={enrollCourseId}
                  onChange={e => setEnrollCourseId(e.target.value)}
                >
                  <option value="">{config.selectedUserPanel.enrollForm.selectPlaceholder}</option>
                  {availableCourses.map(c => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
                <button className="btn-primary" onClick={enrollUser}>{config.selectedUserPanel.enrollForm.submitButtonText}</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalMode === 'create' ? config.modal.createTitle : config.modal.editTitle}</h3>
              <button className="btn-close" onClick={() => setModalOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && <div style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{formError}</div>}
                
                <div className="form-group">
                  <label htmlFor="user-email">{config.modal.fields.email.label}</label>
                  <input
                    id="user-email"
                    type="email"
                    required
                    className="form-input"
                    placeholder={config.modal.fields.email.placeholder}
                    value={formData.email}
                    onChange={e => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="user-name">{config.modal.fields.full_name.label}</label>
                  <input
                    id="user-name"
                    type="text"
                    className="form-input"
                    placeholder={config.modal.fields.full_name.placeholder}
                    value={formData.full_name}
                    onChange={e => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                  />
                </div>

                {config.modal.fields.id_proof && (
                  <div className="form-group">
                    <label htmlFor="user-id-proof">{config.modal.fields.id_proof.label}</label>
                    <input
                      id="user-id-proof"
                      type="text"
                      className="form-input"
                      placeholder={config.modal.fields.id_proof.placeholder}
                      value={formData.id_proof || ''}
                      onChange={e => setFormData(prev => ({ ...prev, id_proof: e.target.value }))}
                    />
                  </div>
                )}

                <div className="form-row-layout">
                  <div className="form-group">
                    <label htmlFor="user-role">{config.modal.fields.role.label}</label>
                    <select
                      id="user-role"
                      className="select-input"
                      value={formData.role}
                      onChange={e => setFormData(prev => ({ ...prev, role: e.target.value }))}
                    >
                      {config.modal.fields.role.options.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group" style={{ justifyContent: 'center', paddingTop: '1.2rem' }}>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={e => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                      />
                      {config.modal.fields.is_active.label}
                    </label>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>{config.modal.buttons.cancel}</button>
                <button type="submit" className="btn-primary">{modalMode === 'create' ? config.modal.buttons.createSubmit : config.modal.buttons.editSubmit}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
