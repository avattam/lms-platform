import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

export default function AdminCourses() {
  const [paths, setPaths] = useState([]);
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [videos, setVideos] = useState([]);
  const [newCourse, setNewCourse] = useState({ title: '', description: '', path_id: '', sequence_order: '' });
  const [newVideo, setNewVideo] = useState({ title: '', video_url: '', sequence_order: 1 });
  const [tab, setTab] = useState('courses'); // 'courses' | 'logs'
  const [logs, setLogs] = useState([]);

  // Editing course details state
  const [isEditingCourse, setIsEditingCourse] = useState(false);
  const [editingCourseData, setEditingCourseData] = useState({ title: '', description: '', path_id: '', sequence_order: 0 });

  // Sub-tabs on course detail view state
  const [detailTab, setDetailTab] = useState('videos'); // 'videos' | 'enrollments'

  // Enrollments state
  const [enrollments, setEnrollments] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [enrollUserId, setEnrollUserId] = useState('');
  const [enrollmentsLoading, setEnrollmentsLoading] = useState(false);

  useEffect(() => { fetchData(); }, []);

  async function fetchData() {
    const [p, c] = await Promise.all([api.get('/admin/paths'), api.get('/admin/courses')]);
    setPaths(p.data);
    setCourses(c.data);
  }

  async function fetchEnrollments(courseId) {
    setEnrollmentsLoading(true);
    try {
      const [enrollResp, usersResp] = await Promise.all([
        api.get(`/admin/courses/${courseId}/enrollments`),
        api.get('/admin/users', { params: { limit: 200 } }),
      ]);
      setEnrollments(enrollResp.data);
      setAllUsers(usersResp.data);
    } catch (err) {
      console.error('Failed to fetch enrollments or users:', err);
    } finally {
      setEnrollmentsLoading(false);
    }
  }

  async function openCourse(course) {
    setSelectedCourse(course);
    setIsEditingCourse(false);
    setDetailTab('videos');
    const { data } = await api.get(`/admin/courses/${course.id}/videos`).catch(() => ({ data: [] }));
    setVideos(data);
    fetchEnrollments(course.id);
  }

  async function createCourse() {
    if (!newCourse.title) return;
    const payload = {
      title: newCourse.title,
      description: newCourse.description || null,
      path_id: newCourse.path_id || null,
      sequence_order: newCourse.sequence_order ? parseInt(newCourse.sequence_order, 10) : null,
    };
    await api.post('/admin/courses', payload);
    setNewCourse({ title: '', description: '', path_id: '', sequence_order: '' });
    fetchData();
  }

  async function deleteCourse(id) {
    if (!confirm('Delete this course?')) return;
    await api.delete(`/admin/courses/${id}`);
    setSelectedCourse(null);
    fetchData();
  }

  async function togglePublish(course) {
    await api.patch(`/admin/courses/${course.id}/publish`);
    fetchData();
    if (selectedCourse?.id === course.id) {
      setSelectedCourse(prev => ({ ...prev, is_published: !prev.is_published }));
    }
  }

  async function startEditingCourse() {
    setEditingCourseData({
      title: selectedCourse.title,
      description: selectedCourse.description || '',
      path_id: selectedCourse.path_id || '',
      sequence_order: selectedCourse.sequence_order || 0,
    });
    setIsEditingCourse(true);
  }

  async function saveCourseEdit() {
    if (!editingCourseData.title) return;
    try {
      const payload = {
        title: editingCourseData.title,
        description: editingCourseData.description || null,
        path_id: editingCourseData.path_id || null,
        sequence_order: editingCourseData.sequence_order ? parseInt(editingCourseData.sequence_order, 10) : null,
      };
      const { data } = await api.put(`/admin/courses/${selectedCourse.id}`, payload);
      setSelectedCourse(data);
      setIsEditingCourse(false);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update course');
    }
  }

  async function enrollUser() {
    if (!enrollUserId || !selectedCourse) return;
    try {
      await api.post(`/admin/users/${enrollUserId}/enrollments`, { course_id: selectedCourse.id });
      setEnrollUserId('');
      fetchEnrollments(selectedCourse.id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to enroll user');
    }
  }

  async function removeEnrollment(userId) {
    if (!selectedCourse) return;
    if (!confirm('Remove this user from the course?')) return;
    try {
      await api.delete(`/admin/users/${userId}/enrollments/${selectedCourse.id}`);
      fetchEnrollments(selectedCourse.id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove enrollment');
    }
  }

  async function addVideo() {
    if (!newVideo.title || !newVideo.video_url || !selectedCourse) return;
    await api.post(`/admin/courses/${selectedCourse.id}/videos`, newVideo);
    setNewVideo({ title: '', video_url: '', sequence_order: videos.length + 2 });
    const { data } = await api.get(`/admin/courses/${selectedCourse.id}/videos`).catch(() => ({ data: [] }));
    setVideos(data);
  }

  async function deleteVideo(videoId) {
    await api.delete(`/admin/videos/${videoId}`);
    setVideos(prev => prev.filter(v => v.id !== videoId));
  }

  async function loadLogs() {
    const { data } = await api.get('/admin/logs/views', { params: { limit: 200 } });
    setLogs(data);
  }

  return (
    <div className="admin-layout">
      <div className="admin-header">
        <h1>Course Administration</h1>
        <div className="tab-bar">
          <button className={`tab ${tab === 'courses' ? 'active' : ''}`} onClick={() => setTab('courses')}>📚 Courses</button>
          <button className={`tab ${tab === 'logs' ? 'active' : ''}`} onClick={() => { setTab('logs'); loadLogs(); }}>📋 View Logs</button>
        </div>
        <Link to="/dashboard" className="btn-ghost">← Dashboard</Link>
      </div>

      {tab === 'courses' && (
        <div className="admin-content">
          {/* Course List */}
          <div className="course-manager">
            <div className="manager-header">
              <h3>All Courses ({courses.length})</h3>
            </div>

            <div className="create-form">
              <h4>Add New Course</h4>
              <input className="form-input" placeholder="Course title" value={newCourse.title}
                onChange={e => setNewCourse(p => ({ ...p, title: e.target.value }))} />
              <input className="form-input" placeholder="Description (optional)" value={newCourse.description}
                onChange={e => setNewCourse(p => ({ ...p, description: e.target.value }))} />
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <select className="select-input" style={{ flex: 1 }} value={newCourse.path_id}
                  onChange={e => setNewCourse(p => ({ ...p, path_id: e.target.value }))}>
                  <option value="">Learning Path (none)</option>
                  {paths.map(p => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </select>
                <input className="form-input" style={{ width: '80px' }} type="number" placeholder="Order" value={newCourse.sequence_order}
                  onChange={e => setNewCourse(p => ({ ...p, sequence_order: e.target.value }))} />
              </div>
              <button className="btn-primary" onClick={createCourse}>+ Add Course</button>
            </div>

            <div className="course-list">
              {courses.map(c => (
                <div key={c.id} className={`course-row ${selectedCourse?.id === c.id ? 'selected' : ''}`}
                  onClick={() => openCourse(c)}>
                  <div className="course-row-info">
                    <span className="course-row-title">{c.title}</span>
                    <span className={`badge ${c.is_published ? 'badge-active' : 'badge-inactive'}`}>
                      {c.is_published ? 'Published' : 'Draft'}
                    </span>
                  </div>
                  <div className="course-row-actions" onClick={e => e.stopPropagation()}>
                    <button className="btn-sm" onClick={() => togglePublish(c)}>
                      {c.is_published ? 'Unpublish' : 'Publish'}
                    </button>
                    <button className="btn-sm btn-danger" onClick={() => deleteCourse(c.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Selected Course Panel */}
          {selectedCourse && (
            <div className="video-manager" style={{ width: '500px' }}>
              {/* Course Detail Section */}
              <div className="course-detail-header" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                {isEditingCourse ? (
                  <div className="edit-course-form" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: '600' }}>Edit Course Details</h4>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Title</label>
                      <input className="form-input" style={{ width: '100%', marginTop: '0.25rem' }} value={editingCourseData.title}
                        onChange={e => setEditingCourseData(prev => ({ ...prev, title: e.target.value }))} />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Description</label>
                      <textarea className="form-input" style={{ width: '100%', minHeight: '60px', fontFamily: 'inherit', marginTop: '0.25rem' }} value={editingCourseData.description}
                        onChange={e => setEditingCourseData(prev => ({ ...prev, description: e.target.value }))} />
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Learning Path</label>
                        <select className="select-input" style={{ width: '100%', marginTop: '0.25rem' }} value={editingCourseData.path_id}
                          onChange={e => setEditingCourseData(prev => ({ ...prev, path_id: e.target.value }))}>
                          <option value="">None</option>
                          {paths.map(p => (
                            <option key={p.id} value={p.id}>{p.title}</option>
                          ))}
                        </select>
                      </div>
                      <div style={{ width: '100px' }}>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Order</label>
                        <input type="number" className="form-input" style={{ width: '100%', marginTop: '0.25rem' }} value={editingCourseData.sequence_order}
                          onChange={e => setEditingCourseData(prev => ({ ...prev, sequence_order: e.target.value }))} />
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                      <button className="btn-primary btn-sm" onClick={saveCourseEdit}>Save</button>
                      <button className="btn-ghost btn-sm" onClick={() => setIsEditingCourse(false)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                      <h3 style={{ fontSize: '1.2rem', fontWeight: '600' }}>{selectedCourse.title}</h3>
                      <button className="btn-sm" onClick={startEditingCourse}>Edit Details</button>
                    </div>
                    <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                      {selectedCourse.description || 'No description provided.'}
                    </p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                      {selectedCourse.path_id && (
                        <span className="badge" style={{ fontSize: '0.75rem', background: 'rgba(108,99,255,0.15)', color: 'var(--primary-light)' }}>
                          Path: {paths.find(p => p.id === selectedCourse.path_id)?.title || 'Unknown'}
                        </span>
                      )}
                      <span className="badge" style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
                        Sequence: {selectedCourse.sequence_order ?? 'None'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Sub-tabs */}
              <div className="tab-bar" style={{ marginBottom: '1rem' }}>
                <button className={`tab ${detailTab === 'videos' ? 'active' : ''}`} onClick={() => setDetailTab('videos')}>
                  🎥 Videos ({videos.length})
                </button>
                <button className={`tab ${detailTab === 'enrollments' ? 'active' : ''}`} onClick={() => setDetailTab('enrollments')}>
                  👥 Enrollments ({enrollments.length})
                </button>
              </div>

              {/* Videos Sub-tab */}
              {detailTab === 'videos' && (
                <div>
                  <div className="create-form">
                    <h4>Add Video</h4>
                    <input className="form-input" placeholder="Video title"
                      value={newVideo.title} onChange={e => setNewVideo(p => ({ ...p, title: e.target.value }))} />
                    <input className="form-input" placeholder="Video URL (file path or stream URL)"
                      value={newVideo.video_url} onChange={e => setNewVideo(p => ({ ...p, video_url: e.target.value }))} />
                    <input className="form-input" type="number" placeholder="Order"
                      value={newVideo.sequence_order} onChange={e => setNewVideo(p => ({ ...p, sequence_order: +e.target.value }))} />
                    <button className="btn-primary" onClick={addVideo}>+ Add Video</button>
                  </div>

                  {videos.length === 0
                    ? <p className="empty-text">No videos yet.</p>
                    : videos.map((v, i) => (
                        <div key={v.id} className="video-row">
                          <span className="video-num">{i + 1}</span>
                          <div className="video-row-info">
                            <span>{v.title}</span>
                            <span className="video-url-preview">{v.video_url}</span>
                          </div>
                          <div className="video-row-actions">
                            <button className="btn-sm" onClick={async () => {
                              await api.patch(`/admin/videos/${v.id}/publish`);
                              const { data } = await api.get(`/admin/courses/${selectedCourse.id}/videos`).catch(() => ({ data: [] }));
                              setVideos(data);
                            }}>
                              {v.is_published ? 'Unpublish' : 'Publish'}
                            </button>
                            <button className="btn-sm btn-danger" onClick={() => deleteVideo(v.id)}>Delete</button>
                          </div>
                        </div>
                      ))
                  }
                </div>
              )}

              {/* Enrollments Sub-tab */}
              {detailTab === 'enrollments' && (
                <div>
                  <div className="create-form">
                    <h4>Enroll User</h4>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <select
                        className="select-input"
                        value={enrollUserId}
                        onChange={e => setEnrollUserId(e.target.value)}
                        style={{ flex: 1 }}
                      >
                        <option value="">Select user...</option>
                        {allUsers
                          .filter(u => !enrollments.some(e => e.id === u.id))
                          .map(u => (
                            <option key={u.id} value={u.id}>
                              {u.full_name ? `${u.full_name} (${u.email})` : u.email}
                            </option>
                          ))
                        }
                      </select>
                      <button className="btn-primary" onClick={enrollUser} disabled={!enrollUserId}>
                        Enroll
                      </button>
                    </div>
                  </div>

                  {enrollmentsLoading ? (
                    <p className="empty-text">Loading enrollments...</p>
                  ) : enrollments.length === 0 ? (
                    <p className="empty-text">No active enrollments for this course.</p>
                  ) : (
                    enrollments.map(user => (
                      <div key={user.id} className="enrollment-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.75rem', background: 'var(--bg-3)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', marginBottom: '0.5rem' }}>
                        <div>
                          <div style={{ fontWeight: '500', fontSize: '0.875rem' }}>{user.full_name || '—'}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email}</div>
                        </div>
                        <button className="btn-sm btn-danger" onClick={() => removeEnrollment(user.id)}>
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'logs' && (
        <div className="logs-panel">
          <h3>Course View Audit Log ({logs.length} sessions)</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>User ID</th><th>Course ID</th><th>Video ID</th>
                <th>Session Start</th><th>Duration (s)</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.id}>
                  <td className="td-mono">{l.user_id?.slice(0, 8)}…</td>
                  <td className="td-mono">{l.course_id?.slice(0, 8)}…</td>
                  <td className="td-mono">{l.video_id?.slice(0, 8)}…</td>
                  <td>{new Date(l.session_start).toLocaleString()}</td>
                  <td>{l.duration_secs ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
