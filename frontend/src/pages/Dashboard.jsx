import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client';

export default function Dashboard({ user, setUser }) {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/courses').then(r => setCourses(r.data)).finally(() => setLoading(false));
  }, []);

  function logout() {
    localStorage.removeItem('lms_token');
    setUser(null);
    navigate('/login');
  }

  return (
    <div className="dashboard-layout">
      <nav className="top-nav">
        <div className="nav-brand">🎓 LMS Platform</div>
        <div className="nav-links">
          <Link to="/chat" className="nav-link">💬 AI Tutor</Link>
          {user.role === 'admin' && (
            <>
              <Link to="/admin/users" className="nav-link">👥 Users</Link>
              <Link to="/admin/courses" className="nav-link">📚 Courses</Link>
            </>
          )}
        </div>
        <div className="nav-user">
          {user.avatar_url && <img src={user.avatar_url} className="avatar" alt="avatar" />}
          <span>{user.full_name || user.email}</span>
          <button className="btn-ghost" onClick={logout}>Sign out</button>
        </div>
      </nav>

      <main className="dashboard-main">
        <header className="dashboard-hero">
          <h1>Welcome back, {user.full_name?.split(' ')[0] || 'Learner'} 👋</h1>
          <p>Pick up where you left off or explore your enrolled courses.</p>
        </header>

        <section className="courses-grid-section">
          <h2>My Courses</h2>
          {loading ? (
            <div className="loading-cards">{[...Array(3)].map((_, i) => <div key={i} className="card-skeleton" />)}</div>
          ) : courses.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">📭</span>
              <p>You haven't been enrolled in any courses yet.</p>
              <p>Contact your administrator to get started.</p>
            </div>
          ) : (
            <div className="courses-grid">
              {courses.map(course => (
                <Link key={course.id} to={`/courses/${course.id}`} className="course-card">
                  {course.thumbnail_url
                    ? <img src={course.thumbnail_url} alt={course.title} className="course-thumb" />
                    : <div className="course-thumb-placeholder">📖</div>
                  }
                  <div className="course-card-body">
                    <h3>{course.title}</h3>
                    <p>{course.description || 'No description available.'}</p>
                    <span className="btn-start">Continue →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
