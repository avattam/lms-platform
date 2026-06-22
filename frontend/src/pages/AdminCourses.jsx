import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

export default function AdminCourses() {
  const [paths, setPaths] = useState([]);
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [videos, setVideos] = useState([]);
  const [newCourse, setNewCourse] = useState({ title: '', description: '' });
  const [newVideo, setNewVideo] = useState({ title: '', video_url: '', sequence_order: 1 });
  const [tab, setTab] = useState('courses'); // 'courses' | 'logs'
  const [logs, setLogs] = useState([]);

  useEffect(() => { fetchData(); }, []);

  async function fetchData() {
    const [p, c] = await Promise.all([api.get('/admin/paths'), api.get('/admin/courses')]);
    setPaths(p.data);
    setCourses(c.data);
  }

  async function openCourse(course) {
    setSelectedCourse(course);
    const { data } = await api.get(`/courses/${course.id}/videos`).catch(() => ({ data: [] }));
    // Admin uses a different approach — fetch all videos
    const vResp = await api.get(`/admin/courses`).catch(() => ({ data: [] }));
    setVideos(data);
  }

  async function createCourse() {
    if (!newCourse.title) return;
    await api.post('/admin/courses', newCourse);
    setNewCourse({ title: '', description: '' });
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

  async function addVideo() {
    if (!newVideo.title || !newVideo.video_url || !selectedCourse) return;
    await api.post(`/admin/courses/${selectedCourse.id}/videos`, newVideo);
    setNewVideo({ title: '', video_url: '', sequence_order: videos.length + 2 });
    const { data } = await api.get(`/courses/${selectedCourse.id}/videos`).catch(() => ({ data: [] }));
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
              <input className="form-input" placeholder="Course title" value={newCourse.title}
                onChange={e => setNewCourse(p => ({ ...p, title: e.target.value }))} />
              <input className="form-input" placeholder="Description (optional)" value={newCourse.description}
                onChange={e => setNewCourse(p => ({ ...p, description: e.target.value }))} />
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

          {/* Video Manager */}
          {selectedCourse && (
            <div className="video-manager">
              <h3>Videos — {selectedCourse.title}</h3>

              <div className="create-form">
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
                        <button className="btn-sm" onClick={() => api.patch(`/admin/videos/${v.id}/publish`)}>
                          {v.is_published ? 'Unpublish' : 'Publish'}
                        </button>
                        <button className="btn-sm btn-danger" onClick={() => deleteVideo(v.id)}>Delete</button>
                      </div>
                    </div>
                  ))
              }
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
