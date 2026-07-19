import React from 'react';

export default function ActivityLog({ entries }) {
  return (
    <section className="activity-log">
      <h2>Learning Activity Log</h2>
      {entries.length === 0 ? (
        <p className="empty-log">No activities recorded yet. Interact with the visualization to see logged events.</p>
      ) : (
        <ul className="log-list">
          {entries.map((entry, idx) => (
            <li key={idx}>
              <time>{entry.timestamp}</time>
              <span>{entry.message}</span>
            </li>
          ))}
        </ul>
      )}
      <style>{`
        .activity-log {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.08);
          margin-top: 20px;
        }
        .activity-log h2 {
          font-size: 1.3rem;
          margin-bottom: 12px;
        }
        .empty-log {
          color: #64748b;
          font-style: italic;
        }
        .log-list {
          list-style: none;
          max-height: 250px;
          overflow-y: auto;
          padding: 0;
        }
        .log-list li {
          display: flex;
          gap: 12px;
          padding: 6px 0;
          border-bottom: 1px solid #f1f5f9;
          font-size: 0.9rem;
        }
        .log-list li time {
          color: #64748b;
          font-family: monospace;
          min-width: 80px;
        }
      `}</style>
    </section>
  );
}