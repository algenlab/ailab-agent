import React, { useRef, useEffect } from 'react';

/**
 * LogPanel — displays a scrollable activity log of learner actions.
 *
 * Props:
 *   entries : array of { id, timestamp, type, message, icon }
 */
export default function LogPanel({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries.length]);

  return (
    <div className="log-panel" role="log" aria-label="Activity log" aria-live="polite">
      {entries.length === 0 && (
        <div style={{ color: 'var(--color-slate-400)', fontStyle: 'italic', padding: '0.5rem 0' }}>
          No activity yet. Navigate through the algorithm steps or answer quiz questions to see your activity here.
        </div>
      )}
      {entries.map((entry) => (
        <div key={entry.id} className="log-entry">
          <span className="log-time">{entry.timestamp}</span>
          <span className={`log-icon ${entry.iconType}`}>
            {entry.iconType === 'correct' && '✓'}
            {entry.iconType === 'incorrect' && '✗'}
            {entry.iconType === 'info' && '→'}
            {entry.iconType === 'hint' && '💡'}
            {entry.iconType === 'reveal' && '👁'}
          </span>
          <span className="log-message">{entry.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
