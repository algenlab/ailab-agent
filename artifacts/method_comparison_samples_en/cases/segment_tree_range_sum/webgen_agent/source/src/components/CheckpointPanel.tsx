import React, { useState } from 'react';
import { Checkpoint } from '../types';

interface Props {
  checkpoints: Checkpoint[];
  activeCheckpoint: number;
  onSelectCheckpoint: (id: number) => void;
  responses: Record<number, string>;
  results: Record<number, boolean | null>;
  showHints: Record<number, boolean>;
  showAnswers: Record<number, boolean>;
  hints: Record<number, string>;
  answers: Record<number, string>;
  onSubmit: (id: number, answer: string) => void;
  onShowHint: (id: number) => void;
  onShowAnswer: (id: number) => void;
  currentStep: string;
}

const panelStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-md)',
  padding: '20px',
  boxShadow: 'var(--shadow)',
  minHeight: '320px',
};

const tabStyle: React.CSSProperties = {
  display: 'flex',
  gap: '6px',
  marginBottom: '16px',
  flexWrap: 'wrap',
};

function tabBtnStyle(active: boolean): React.CSSProperties {
  return {
    padding: '6px 14px',
    borderRadius: '20px',
    border: active ? '2px solid #7c3aed' : '1px solid #475569',
    background: active ? '#5b21b6' : 'transparent',
    color: active ? '#f1f5f9' : '#94a3b8',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  };
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 14px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid #475569',
  background: '#0f172a',
  color: '#f1f5f9',
  fontSize: '0.9rem',
  marginTop: '10px',
};

const btnSmall: React.CSSProperties = {
  padding: '7px 16px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid #475569',
  background: '#334155',
  color: '#e2e8f0',
  fontWeight: 600,
  fontSize: '0.8rem',
  cursor: 'pointer',
  marginRight: '8px',
  marginTop: '10px',
};

const successBadge: React.CSSProperties = {
  display: 'inline-block',
  background: '#065f46',
  color: '#4ade80',
  padding: '2px 10px',
  borderRadius: '12px',
  fontSize: '0.75rem',
  fontWeight: 700,
  marginLeft: '8px',
};

const errorBadge: React.CSSProperties = {
  display: 'inline-block',
  background: '#7f1d1d',
  color: '#fca5a5',
  padding: '2px 10px',
  borderRadius: '12px',
  fontSize: '0.75rem',
  fontWeight: 700,
  marginLeft: '8px',
};

export default function CheckpointPanel({
  checkpoints,
  activeCheckpoint,
  onSelectCheckpoint,
  responses,
  results,
  showHints,
  showAnswers,
  hints,
  answers,
  onSubmit,
  onShowHint,
  onShowAnswer,
}: Props) {
  const [inputValue, setInputValue] = useState('');

  const active =
    checkpoints.find((c) => c.id === activeCheckpoint) || checkpoints[0];

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onSubmit(active.id, inputValue.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div style={panelStyle}>
      <h3
        style={{
          fontSize: '1rem',
          fontWeight: 700,
          color: '#e2e8f0',
          marginBottom: '12px',
        }}
      >
        🧠 Checkpoint Questions
      </h3>
      <div style={tabStyle}>
        {checkpoints.map((cp) => {
          const result = results[cp.id];
          let icon = '';
          if (result === true) icon = ' ✅';
          else if (result === false) icon = ' ❌';
          return (
            <button
              key={cp.id}
              style={tabBtnStyle(cp.id === activeCheckpoint)}
              onClick={() => {
                setInputValue('');
                onSelectCheckpoint(cp.id);
              }}
              aria-label={`Question ${cp.id}`}
            >
              Q{cp.id}{icon}
            </button>
          );
        })}
      </div>

      <div style={{ marginBottom: '12px' }}>
        <p
          style={{
            color: '#cbd5e1',
            fontSize: '0.9rem',
            lineHeight: 1.7,
          }}
        >
          {active.question}
        </p>
        {results[active.id] === true && (
          <span style={successBadge}>Correct</span>
        )}
        {results[active.id] === false && (
          <span style={errorBadge}>Incorrect</span>
        )}
      </div>

      <input
        style={inputStyle}
        type="text"
        placeholder="Type your answer..."
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-label="Your answer"
        disabled={results[active.id] === true}
      />

      <div>
        <button
          style={btnSmall}
          onClick={handleSubmit}
          disabled={results[active.id] === true || !inputValue.trim()}
        >
          Submit
        </button>
        <button
          style={btnSmall}
          onClick={() => onShowHint(active.id)}
          aria-label="Toggle hint"
        >
          {showHints[active.id] ? 'Hide Hint' : '💡 Hint'}
        </button>
        <button
          style={btnSmall}
          onClick={() => onShowAnswer(active.id)}
          aria-label="Show answer"
        >
          👁️ Show Answer
        </button>
      </div>

      {showHints[active.id] && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px 14px',
            background: '#1e293b',
            borderLeft: '3px solid #fbbf24',
            borderRadius: 'var(--radius-sm)',
            color: '#fbbf24',
            fontSize: '0.85rem',
          }}
        >
          {hints[active.id]}
        </div>
      )}

      {showAnswers[active.id] && (
        <div
          style={{
            marginTop: '8px',
            padding: '10px 14px',
            background: '#0f2b1a',
            borderLeft: '3px solid #10b981',
            borderRadius: 'var(--radius-sm)',
            color: '#4ade80',
            fontSize: '0.85rem',
          }}
        >
          <strong>Answer:</strong> {answers[active.id]}
        </div>
      )}

      {responses[active.id] && (
        <div
          style={{
            marginTop: '8px',
            fontSize: '0.8rem',
            color: '#94a3b8',
          }}
        >
          Your response: <em>"{responses[active.id]}"</em>
        </div>
      )}
    </div>
  );
}
