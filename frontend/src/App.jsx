import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from './api/client';
import AuthCallback from './pages/AuthCallback';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CoursePlayer from './pages/CoursePlayer';
import Chat from './pages/Chat';
import Assessment from './pages/Assessment';
import AdminUsers from './pages/AdminUsers';
import AdminCourses from './pages/AdminCourses';
import './index.css';

function ProtectedRoute({ user, children, adminOnly = false }) {
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('lms_token');
    if (!token) { setLoading(false); return; }
    api.get('/auth/me')
      .then(r => setUser(r.data))
      .catch(() => localStorage.removeItem('lms_token'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback setUser={setUser} />} />
        <Route path="/dashboard" element={
          <ProtectedRoute user={user}><Dashboard user={user} setUser={setUser} /></ProtectedRoute>
        } />
        <Route path="/courses/:courseId" element={
          <ProtectedRoute user={user}><CoursePlayer user={user} /></ProtectedRoute>
        } />
        <Route path="/chat" element={
          <ProtectedRoute user={user}><Chat user={user} /></ProtectedRoute>
        } />
        <Route path="/assessment/:id" element={
          <ProtectedRoute user={user}><Assessment user={user} /></ProtectedRoute>
        } />
        <Route path="/admin/users" element={
          <ProtectedRoute user={user} adminOnly><AdminUsers /></ProtectedRoute>
        } />
        <Route path="/admin/courses" element={
          <ProtectedRoute user={user} adminOnly><AdminCourses /></ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
