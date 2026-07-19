import React from 'react';

export default function LearningLog({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="learning-log">
        <h3>Learning Log</h3>
        <p className="log-empty">No activities yet. Start exploring the algorithm steps or answer checkpoint questions.</p>
      </div>
    );
  }

  return (
    <div className="learning-log">
      <h3>Learning Log</h3>
      <div className="log-entries">
        {entries.map((entry, idx) => (
          <div key={idx} className="log-entry">
            <span className="log-time">{new Date(entry.timestamp).toLocaleTimeString()}</span>
            <span className={`log-type log-type-${entry.type}`}>
              {entry.type === 'navigation' && '📍 Navigation'}
              {entry.type === 'checkpoint' && (entry.correct ? '✅ Correct Answer' : '❌ Incorrect Answer')}
              {entry.type === 'hint' && '💡 Hint Requested'}
              {entry.type === 'show_answer' && '👁 Answer Revealed'}
            </span>
            <span className="log-detail">
              {entry.type === 'navigation' && `${entry.direction === 'next' ? 'Moved to' : 'Returned to'} Step ${entry.step}`}
              {entry.type === 'checkpoint' && `Question: ${entry.question}`}
              {entry.type === 'hint' && `Question: ${entry.question}`}
              {entry.type === 'show_answer' && `Question: ${entry.question}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}