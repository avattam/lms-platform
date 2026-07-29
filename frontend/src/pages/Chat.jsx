import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import FormattedMessage from '../components/FormattedMessage';

const SESSION_ID = `chat-${Date.now()}`;

const SUGGESTION_CHIPS = [
  'What courses are available?',
  'Explain Naturopathic medicine',
  'Check my learning progress',
  'Quiz me on course material',
];

export default function Chat({ user, theme, setTheme }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [agentStatus, setAgentStatus] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    // Load history for this session
    api.get(`/chat/sessions/${SESSION_ID}/history`)
      .then(r => setMessages(r.data.map(m => ({ role: m.role, content: m.content, sources: m.sources }))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentStatus]);

  async function sendMessage(overrideText = null) {
    const userMsg = (overrideText || input).trim();
    if (!userMsg || streaming) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'human', content: userMsg }]);
    setStreaming(true);
    setAgentStatus('⚡ Agent initializing...');

    // Add empty AI message to stream into
    setMessages(prev => [...prev, { role: 'ai', content: '', sources: [] }]);

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
          const payloadStr = line.slice(6).trim();
          if (payloadStr === '[DONE]') break;

          try {
            const data = JSON.parse(payloadStr);

            if (data.type === 'thought') {
              setAgentStatus(data.status || '🧠 Reasoning...');
            } else if (data.type === 'sources') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === 'ai') {
                  updated[updated.length - 1] = {
                    ...last,
                    sources: data.sources || [],
                  };
                }
                return updated;
              });
            } else if (data.type === 'token') {
              setAgentStatus(''); // Clear status once text streams
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === 'ai') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + data.token,
                  };
                }
                return updated;
              });
            } else if (data.type === 'done') {
              setAgentStatus('');
            } else if (data.token) {
              // Backward compatibility
              setAgentStatus('');
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === 'ai') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + data.token,
                  };
                }
                return updated;
              });
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'ai', content: '⚠️ Failed to get a response from agent.' };
        return updated;
      });
    } finally {
      setStreaming(false);
      setAgentStatus('');
    }
  }

  return (
    <div className="chat-layout">
      <nav className="chat-nav">
        <Link to="/dashboard" className="btn-ghost">← Dashboard</Link>
        <h2>AI Tutor Agent</h2>
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
            <h3>Hello! I'm your Agentic AI Learning Assistant.</h3>
            <p>I can search course materials, check course catalogs, evaluate answers, and track your progress.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'human' ? 'bubble-user' : 'bubble-ai'}`}>
            <div className="bubble-avatar">{m.role === 'human' ? '🧑' : '🤖'}</div>
            <div className="bubble-content">
              <FormattedMessage content={m.content} />

              {/* Display Sources retrieved by Agent */}
              {m.sources && m.sources.length > 0 && (
                <div className="chat-sources-box">
                  <div className="sources-title">📚 Retrieved Sources ({m.sources.length}):</div>
                  <div className="sources-list">
                    {m.sources.map((s, idx) => (
                      <div key={idx} className="source-card" title={s.snippet}>
                        <span className="source-icon">📄</span>
                        <span className="source-name">{s.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {streaming && i === messages.length - 1 && m.role === 'ai' && (
                <span className="cursor-blink">▋</span>
              )}
            </div>
          </div>
        ))}

        {/* Active Agent Thinking / Tool Execution Badge */}
        {streaming && agentStatus && (
          <div className="agent-status-badge">
            <span className="spinner">⏳</span>
            <span>{agentStatus}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick Action Suggestion Chips */}
      {messages.length < 4 && !streaming && (
        <div className="chat-chips-container">
          {SUGGESTION_CHIPS.map((chip, i) => (
            <button key={i} className="suggestion-chip" onClick={() => sendMessage(chip)}>
              💡 {chip}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-bar">
        <input
          className="chat-input"
          placeholder="Ask AI Tutor about your course material…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          disabled={streaming}
        />
        <button className="btn-send" onClick={() => sendMessage()} disabled={streaming || !input.trim()}>
          {streaming ? '⟳' : '↑'}
        </button>
      </div>
    </div>
  );
}
