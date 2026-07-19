import React from 'react';
import './LearningLog.css';

export default function LearningLog({ entries }) {
  return (
    <section className="learning-log" aria-label="Learning Activity Log">
      <h2 className="section-title">Learning Log</h2>
      <div className="log-container">
        {entries.length === 0 ? (
          <p className="log-empty">No actions recorded yet. Interact with the visualizations and checkpoints.</p>
        ) : (
          <ul className="log-list">
            {entries.map(entry => (
              <li key={entry.id} className="log-entry">
                <span className="log-time">{entry.timestamp}</span>
                <span className="log-message">{entry.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
