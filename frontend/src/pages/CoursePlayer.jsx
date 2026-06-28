import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';

const HEARTBEAT_MS = 10_000;

function getPlayerTypeAndUrl(url) {
  if (!url) return { type: 'none', url: '' };

  let resolvedUrl = url;
  if (url.startsWith('/')) {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    resolvedUrl = `${baseUrl}${url}`;
  }

  // 1. YouTube
  const ytMatch = resolvedUrl.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i);
  if (ytMatch) {
    const videoId = ytMatch[1];
    return {
      type: 'youtube',
      url: `https://www.youtube.com/embed/${videoId}?enablejsapi=1&rel=0`
    };
  }

  // 2. Google Drive / Docs / Slides / Sheets
  const isGoogle = resolvedUrl.includes('drive.google.com') || resolvedUrl.includes('docs.google.com');
  if (isGoogle) {
    const driveIdMatch = resolvedUrl.match(/\/d\/([a-zA-Z0-9_-]{25,110})/i) || resolvedUrl.match(/[?&]id=([a-zA-Z0-9_-]{25,110})/i);
    if (driveIdMatch) {
      const fileId = driveIdMatch[1];
      if (resolvedUrl.includes('/presentation')) {
        return {
          type: 'google-slides',
          url: `https://docs.google.com/presentation/d/${fileId}/embed`
        };
      } else if (resolvedUrl.includes('/document')) {
        return {
          type: 'google-docs',
          url: `https://docs.google.com/document/d/${fileId}/preview`
        };
      } else if (resolvedUrl.includes('/spreadsheets')) {
        return {
          type: 'google-sheets',
          url: `https://docs.google.com/spreadsheets/d/${fileId}/preview`
        };
      } else {
        return {
          type: 'google-drive',
          url: `https://drive.google.com/file/d/${fileId}/preview`
        };
      }
    }
  }

  return {
    type: 'video',
    url: resolvedUrl
  };
}

export default function CoursePlayer({ user, theme, setTheme }) {
  const { courseId } = useParams();
  const [videos, setVideos] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [tab, setTab] = useState('videos'); // 'videos' | 'documents'
  const [current, setCurrent] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const videoRef = useRef(null);
  const heartbeatRef = useRef(null);
  const elapsedTimeRef = useRef(0);

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
      .catch(() => { });
  }, [courseId]);

  async function loadVideo(video) {
    // End previous session if active
    if (sessionId) await endSession();

    setCurrent(video);
    setElapsedTime(0);
    elapsedTimeRef.current = 0;
    setIsCompleted(false);

    // Fetch resume position
    const { data: progress } = await api.get(`/video/${video.id}/progress`);
    setIsCompleted(progress.completed);

    // Start audit session
    const { data: session } = await api.post(`/video/${video.id}/session/start`);
    setSessionId(session.session_id);

    const initialPos = progress.last_position_secs || 0;
    elapsedTimeRef.current = initialPos;
    setElapsedTime(initialPos);

    // Seek to last position after video loads (for native video element)
    const info = getPlayerTypeAndUrl(video.video_url);
    if (info.type === 'video') {
      setTimeout(() => {
        const el = videoRef.current;
        if (el) {
          el.onloadedmetadata = () => {
            if (initialPos > 0 && !progress.completed) {
              el.currentTime = initialPos;
            }
          };
          if (el.readyState >= 1) {
            if (initialPos > 0 && !progress.completed) {
              el.currentTime = initialPos;
            }
          }
        }
      }, 50);
    }
  }

  // Increment elapsed time for iframe videos every second
  useEffect(() => {
    if (!current) return;
    const info = getPlayerTypeAndUrl(current.video_url);
    if (info.type === 'video') return;

    const timer = setInterval(() => {
      elapsedTimeRef.current += 1;
      setElapsedTime(elapsedTimeRef.current);
    }, 1000);

    return () => clearInterval(timer);
  }, [current]);

  // Heartbeat — save progress every 10s
  useEffect(() => {
    if (!current) return;
    heartbeatRef.current = setInterval(saveProgress, HEARTBEAT_MS);
    return () => clearInterval(heartbeatRef.current);
  }, [current]);

  async function saveProgress(completed = false) {
    if (!current) return;

    let position = 0;
    let duration = current.duration_secs || 0;

    const info = getPlayerTypeAndUrl(current.video_url);
    if (info.type === 'video') {
      const el = videoRef.current;
      if (el) {
        position = Math.floor(el.currentTime);
        duration = el.duration || duration;
      }
    } else {
      position = elapsedTimeRef.current;
    }

    await api.patch(`/video/${current.id}/progress`, {
      position_secs: position,
      watch_percent: duration ? (position / duration) * 100 : 0,
      completed,
    }).catch(() => { });
  }

  async function endSession() {
    if (!sessionId || !current) return;
    await saveProgress();
    await api.post(`/video/${current.id}/session/end`, { session_id: sessionId }).catch(() => { });
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
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <Link to="/dashboard" className="btn-ghost" style={{ flex: 1, textAlign: 'center', fontSize: '0.85rem', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.5rem' }}>
            ← Back
          </Link>
          <button 
            className="btn-ghost" 
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.6rem' }}
            title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

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
              {(() => {
                const info = getPlayerTypeAndUrl(current.video_url);
                if (info.type === 'video') {
                  return (
                    <video
                      ref={videoRef}
                      src={info.url}
                      controls
                      className="video-player"
                      onEnded={() => {
                        saveProgress(true);
                        setIsCompleted(true);
                      }}
                    />
                  );
                }
                return (
                  <div className="iframe-player-wrapper" style={{ position: 'relative', width: '100%', aspectRatio: '16/9', background: '#000', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <iframe
                      src={info.url}
                      title={current.title}
                      width="100%"
                      height="100%"
                      allow="autoplay; encrypted-media; fullscreen"
                      allowFullScreen
                      style={{ border: 'none', position: 'absolute', top: 0, left: 0 }}
                    />
                  </div>
                );
              })()}

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem', background: 'var(--bg-3)', padding: '0.75rem 1.25rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: '500', color: isCompleted ? 'var(--success)' : 'var(--text-muted)' }}>
                    {isCompleted ? '✅ Completed' : '⏳ In Progress'}
                  </span>
                  {getPlayerTypeAndUrl(current.video_url).type !== 'video' && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      • Watch Time: {Math.floor(elapsedTime / 60)}m {elapsedTime % 60}s
                    </span>
                  )}
                </div>
                {!isCompleted && (
                  <button
                    className="btn-primary"
                    onClick={() => {
                      saveProgress(true);
                      setIsCompleted(true);
                    }}
                    style={{ padding: '0.4rem 1rem', fontSize: '0.85rem', boxShadow: 'none' }}
                  >
                    Mark as Completed
                  </button>
                )}
              </div>

              {current.description && <p className="video-desc" style={{ marginTop: '1.25rem' }}>{current.description}</p>}
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

