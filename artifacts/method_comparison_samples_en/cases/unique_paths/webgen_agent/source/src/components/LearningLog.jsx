import React from 'react';

export default function LearningLog({ entries }) {
  if (entries.length === 0) {
    return (
      <div className="learning-log">
        <h3 className="section-title">Learning Log</h3>
        <p className="log-empty">No activity recorded yet. Start exploring the DP table or try a checkpoint.</p>
      </div>
    );
  }

  return (
    <div className="learning-log">
      <h3 className="section-title">Learning Log</h3>
      <ul className="log-list">
        {entries.map((entry) => (
          <li key={entry.id} className="log-entry">
            <span className="log-time">{entry.time}</span>
            <span className="log-message">{entry.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
