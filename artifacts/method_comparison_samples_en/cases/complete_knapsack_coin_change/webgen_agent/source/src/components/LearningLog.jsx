import React, { useRef, useEffect } from 'react';

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function LearningLog({ entries }) {
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries.length]);

  if (entries.length === 0) {
    return (
      <div className="learning-log">
        <h3 className="section-title">Learning Log</h3>
        <p className="log-empty">No activity yet. Navigate through the steps or answer checkpoint questions to see your activity logged here.</p>
      </div>
    );
  }

  return (
    <div className="learning-log">
      <h3 className="section-title">Learning Log</h3>
      <div className="log-entries">
        {entries.map((entry, i) => (
          <div key={i} className={`log-entry log-entry-${entry.type}`}>
            <span className="log-time">{formatTime(entry.timestamp)}</span>
            <span className={`log-icon log-icon-${entry.type}`}>
              {entry.type === 'correct' ? '✅' :
               entry.type === 'incorrect' ? '❌' :
               entry.type === 'hint' ? '💡' :
               entry.type === 'reveal' ? '👁' :
               entry.type === 'navigate' ? '▶' :
               entry.type === 'checkpoint-reached' ? '🎯' : '📝'}
            </span>
            <span className="log-message">{entry.message}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
