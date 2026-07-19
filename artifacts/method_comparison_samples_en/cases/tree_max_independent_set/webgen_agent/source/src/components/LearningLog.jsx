import React, { useEffect, useRef } from 'react';

export default function LearningLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  function getClassName(entry) {
    if (entry.type === 'correct') return 'log-entry correct-log';
    if (entry.type === 'incorrect') return 'log-entry incorrect-log';
    if (entry.type === 'hint') return 'log-entry hint-log';
    return 'log-entry';
  }

  return (
    <div className="learning-log">
      <h2>📝 Learning Log</h2>
      {entries.length === 0 && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No activity yet.</p>}
      {entries.map(entry => (
        <div key={entry.id} className={getClassName(entry)}>
          <span className="log-time">{entry.time}</span>
          <span className="log-message">{entry.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}