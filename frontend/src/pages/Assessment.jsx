import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api/client';

export default function Assessment({ user }) {
  const { id: assessmentId } = useParams();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/assessment/${assessmentId}/questions`).then(r => setQuestions(r.data)).catch(() => {});
    api.get(`/assessment/${assessmentId}/attempts`).then(r => setAttempts(r.data)).catch(() => {});
  }, [assessmentId]);

  function handleAnswer(questionId, value) {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  }

  async function submit() {
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        assessment_id: assessmentId,
        answers: Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer })),
      };
      const { data } = await api.post('/assessment/submit', payload);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    const pct = Math.round((result.total_score / result.max_total) * 100);
    return (
      <div className="assessment-result">
        <div className={`result-card ${result.passed ? 'passed' : 'failed'}`}>
          <div className="result-icon">{result.passed ? '🎉' : '📘'}</div>
          <h2>{result.passed ? 'Well Done!' : 'Keep Studying'}</h2>
          <div className="result-score">
            <span className="score-big">{pct}%</span>
            <span>{result.total_score} / {result.max_total} points</span>
          </div>
          <div className="result-feedback">
            {result.feedback.map((f, i) => (
              <div key={i} className={`feedback-item ${f.score === f.max_score ? 'correct' : 'incorrect'}`}>
                <span className="feedback-q">Q{i + 1}</span>
                <span className="feedback-score">{f.score}/{f.max_score}</span>
                {f.ai_reasoning && <p className="feedback-reason">{f.ai_reasoning}</p>}
              </div>
            ))}
          </div>
          <button className="btn-primary" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="assessment-layout">
      <div className="assessment-header">
        <button className="btn-ghost" onClick={() => navigate(-1)}>← Back</button>
        <h2>Assessment</h2>
        <div className="attempt-count">
          Attempts used: {attempts.length} / 3
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="questions-list">
        {questions.map((q, i) => (
          <div key={q.id} className="question-card">
            <div className="question-header">
              <span className="question-num">Q{i + 1}</span>
              <span className={`question-type ${q.question_type}`}>{q.question_type.toUpperCase()}</span>
            </div>
            <p className="question-text">{q.question_text}</p>

            {q.question_type === 'mcq' ? (
              <div className="options-list">
                {(q.options || []).map((opt, j) => (
                  <label key={j} className={`option-label ${answers[q.id] === opt.text ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name={q.id}
                      value={opt.text}
                      checked={answers[q.id] === opt.text}
                      onChange={() => handleAnswer(q.id, opt.text)}
                    />
                    <span className="option-letter">{opt.label}</span>
                    <span>{opt.text}</span>
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                className="free-form-input"
                placeholder="Write your answer here…"
                rows={5}
                value={answers[q.id] || ''}
                onChange={e => handleAnswer(q.id, e.target.value)}
              />
            )}
          </div>
        ))}
      </div>

      <div className="assessment-footer">
        <button
          className="btn-primary btn-submit"
          onClick={submit}
          disabled={submitting || attempts.length >= 3}
        >
          {submitting ? 'Grading…' : 'Submit Assessment'}
        </button>
        {attempts.length >= 3 && (
          <p className="max-attempts-msg">Maximum attempts reached. Contact your instructor.</p>
        )}
      </div>
    </div>
  );
}
