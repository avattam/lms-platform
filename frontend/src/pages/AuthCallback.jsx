import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/client';

export default function AuthCallback({ setUser }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = params.get('token');
    if (!token) { navigate('/login'); return; }
    localStorage.setItem('lms_token', token);
    api.get('/auth/me').then(r => {
      setUser(r.data);
      navigate('/dashboard');
    }).catch(() => navigate('/login'));
  }, []);

  return (
    <div className="loading-screen">
      <div className="spinner" />
      <p>Signing you in…</p>
    </div>
  );
}
