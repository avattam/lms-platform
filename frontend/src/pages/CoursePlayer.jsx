import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';

const HEARTBEAT_MS = 10_000;

export default function CoursePlayer({ user }) {
  const { courseId } = useParams();
  const [videos, setVideos] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [tab, setTab] = useState('videos'); // 'videos' | 'documents'
  const [current, setCurrent] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const videoRef = useRef(null);
  const heartbeatRef = useRef(null);

  // Load video list for the course
  useEffect(() => {
    api.get(`/courses/${courseId}/videos`).then(r => {
      setVideos(r.data);
      if (r.data.length > 0) loadVideo(r.data[0]);
    });
  }, [courseId]);

  // Load documents for the course
  useEffect(() => {
    api.get(`/courses/${courseId}/documents`)
      .then(r => setDocuments(r.data))
      .catch(() => {});
  }, [courseId]);

  async function loadVideo(video) {
    // End previous session if active
    if (sessionId) await endSession();

    setCurrent(video);

    // Fetch resume position
    const { data: progress } = await api.get(`/video/${video.id}/progress`);

    // Start audit session
    const { data: session } = await api.post(`/video/${video.id}/session/start`);
    setSessionId(session.session_id);

    // Seek to last position after video loads
    const el = videoRef.current;
    if (el) {
      el.onloadedmetadata = () => {
        if (progress.last_position_secs > 0 && !progress.completed) {
          el.currentTime = progress.last_position_secs;
        }
      };
    }
  }

  // Heartbeat — save progress every 10s
  useEffect(() => {
    if (!current) return;
    heartbeatRef.current = setInterval(saveProgress, HEARTBEAT_MS);
    return () => clearInterval(heartbeatRef.current);
  }, [current]);

  async function saveProgress(completed = false) {
    if (!videoRef.current || !current) return;
    const el = videoRef.current;
    await api.patch(`/video/${current.id}/progress`, {
      position_secs: Math.floor(el.currentTime),
      watch_percent: el.duration ? (el.currentTime / el.duration) * 100 : 0,
      completed,
    }).catch(() => {});
  }

  async function endSession() {
    if (!sessionId || !current) return;
    await saveProgress();
    await api.post(`/video/${current.id}/session/end`, { session_id: sessionId }).catch(() => {});
    setSessionId(null);
  }

  // Clean up on unmount or tab close
  useEffect(() => {
    const handleUnload = () => endSession();
    window.addEventListener('beforeunload', handleUnload);
    return () => {
      clearInterval(heartbeatRef.current);
      endSession();
      window.removeEventListener('beforeunload', handleUnload);
    };
  }, [sessionId, current]);

  return (
    <div className="player-layout">
      {/* Sidebar */}
      <aside className="video-sidebar">
        <Link to="/dashboard" className="btn-ghost" style={{ display: 'block', marginBottom: '1.25rem', textAlign: 'center', fontSize: '0.85rem' }}>
          ← Back to Dashboard
        </Link>

        {/* Tab Selector */}
        <div className="tab-bar" style={{ marginBottom: '1.25rem' }}>
          <button className={`tab ${tab === 'videos' ? 'active' : ''}`} onClick={() => setTab('videos')} style={{ flex: 1, padding: '0.4rem 0.5rem', fontSize: '0.8rem' }}>
            🎥 Videos
          </button>
          <button className={`tab ${tab === 'documents' ? 'active' : ''}`} onClick={() => setTab('documents')} style={{ flex: 1, padding: '0.4rem 0.5rem', fontSize: '0.8rem' }}>
            📄 Docs
          </button>
        </div>

        {tab === 'videos' ? (
          <>
            <h3>Course Videos</h3>
            {videos.map((v, i) => (
              <button
                key={v.id}
                className={`video-item ${current?.id === v.id ? 'active' : ''}`}
                onClick={() => loadVideo(v)}
              >
                <span className="video-num">{i + 1}</span>
                <span className="video-title">{v.title}</span>
              </button>
            ))}
          </>
        ) : (
          <>
            <h3>Documents List</h3>
            <p className="empty-text" style={{ padding: '0.5rem 0.25rem', fontSize: '0.8rem' }}>
              Select a document in the main area to view or download.
            </p>
          </>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="player-main">
        {tab === 'videos' ? (
          current ? (
            <>
              <h2>{current.title}</h2>
              <video
                ref={videoRef}
                src={current.video_url}
                controls
                className="video-player"
                onEnded={() => saveProgress(true)}
              />
              {current.description && <p className="video-desc">{current.description}</p>}
            </>
          ) : (
            <div className="empty-state">Select a video to begin.</div>
          )
        ) : (
          <div>
            <h2 style={{ marginBottom: '1.5rem' }}>Course Reference Documents</h2>
            
            {documents.length === 0 ? (
              <div className="empty-state">No reference documents uploaded for this course yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {documents.map((doc) => (
                  <div key={doc.id} className="video-row" style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-3)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <span style={{ fontSize: '1.75rem', marginRight: '1rem' }}>📄</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h4 style={{ color: 'var(--text)', fontSize: '0.95rem', fontWeight: '500', marginBottom: '0.2rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {doc.filename}
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {(doc.file_size / 1024).toFixed(1)} KB • Uploaded on {new Date(doc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div>
                      <a 
                        href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${doc.file_url}`} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="btn-primary" 
                        style={{ display: 'inline-flex', alignItems: 'center', padding: '0.5rem 1.2rem', textDecoration: 'none', fontSize: '0.85rem' }}
                      >
                        Download Document
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

