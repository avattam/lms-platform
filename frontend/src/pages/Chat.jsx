import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

const SESSION_ID = `chat-${Date.now()}`;

export default function Chat({ user, theme, setTheme }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    // Load history for this session
    api.get(`/chat/sessions/${SESSION_ID}/history`)
      .then(r => setMessages(r.data.map(m => ({ role: m.role, content: m.content }))));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || streaming) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'human', content: userMsg }]);
    setStreaming(true);

    // Add empty AI message to stream into
    setMessages(prev => [...prev, { role: 'ai', content: '' }]);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('lms_token')}`,
        },
        body: JSON.stringify({ session_id: SESSION_ID, message: userMsg }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') break;
          try {
            const { token } = JSON.parse(payload);
            setMessages(prev => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + token,
              };
              return updated;
            });
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'ai', content: '⚠️ Failed to get a response.' };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="chat-layout">
      <nav className="chat-nav">
        <Link to="/dashboard" className="btn-ghost">← Dashboard</Link>
        <h2>AI Tutor</h2>
        <button 
          className="btn-ghost" 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.6rem' }}
          title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </nav>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <span className="chat-icon">🤖</span>
            <h3>Hello! I'm your AI learning assistant.</h3>
            <p>Ask me anything about your course material.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'human' ? 'bubble-user' : 'bubble-ai'}`}>
            <div className="bubble-avatar">{m.role === 'human' ? '🧑' : '🤖'}</div>
            <div className="bubble-content">
              {m.content}
              {streaming && i === messages.length - 1 && m.role === 'ai' && (
                <span className="cursor-blink">▋</span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <input
          className="chat-input"
          placeholder="Ask about your course material…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          disabled={streaming}
        />
        <button className="btn-send" onClick={sendMessage} disabled={streaming || !input.trim()}>
          {streaming ? '⟳' : '↑'}
        </button>
      </div>
    </div>
  );
}
