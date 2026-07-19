import React, { useEffect, useRef } from 'react';

export default function LearningLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div className="log-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '120px' }}>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
          No activity yet. Interact with the visualization or checkpoint to see your learning log.
        </p>
      </div>
    );
  }

  return (
    <div className="log-container">
      {entries.map((entry) => {
        let actionClass = 'log-action';
        if (entry.action === 'correct') actionClass += ' correct-log';
        else if (entry.action === 'incorrect') actionClass += ' incorrect-log';
        else if (entry.action === 'hint') actionClass += ' hint-log';
        else if (entry.action === 'reveal') actionClass += ' reveal-log';
        else if (entry.action === 'step') actionClass += ' step-log';

        return (
          <div key={entry.id} className="log-entry">
            <span className="log-time">{entry.time}</span>
            <span className={actionClass}>{entry.action}</span>
            <span className="log-detail">{entry.detail}</span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
