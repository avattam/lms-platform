import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api/client';

const HEARTBEAT_MS = 10_000;

export default function CoursePlayer({ user }) {
  const { courseId } = useParams();
  const [videos, setVideos] = useState([]);
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
      {/* Sidebar: video list */}
      <aside className="video-sidebar">
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
      </aside>

      {/* Main: video player */}
      <main className="player-main">
        {current ? (
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
        )}
      </main>
    </div>
  );
}
