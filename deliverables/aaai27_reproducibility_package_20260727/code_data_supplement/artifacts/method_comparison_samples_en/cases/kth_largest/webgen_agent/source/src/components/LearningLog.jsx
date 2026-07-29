import React from 'react';

export default function LearningLog({ entries }) {
  return (
    <div className="learning-log card">
      <h2>Activity Log</h2>
      <ul className="log-list">
        {entries.length === 0 && <li className="empty">No actions yet.</li>}
        {entries.map((entry, idx) => (
          <li key={idx} className="log-entry">
            <span className="log-timestamp">{new Date(entry.timestamp).toLocaleTimeString()}</span>
            <span className="log-message">{entry.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
  