import React, { useRef, useEffect } from 'react';
import './ActivityLog.css';

export default function ActivityLog({ entries }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <section className="activity-log" aria-label="Learning activity log">
      <h2 className="al-title">Activity Log</h2>
      <div className="al-list" ref={listRef} role="log" aria-live="polite">
        {entries.length === 0 ? (
          <p className="al-empty">No activity yet. Interact with the algorithm to see logged events.</p>
        ) : (
          entries.map(entry => (
            <div
              key={entry.id}
              className={`al-entry al-entry-${entry.type} ${entry.correct === true ? 'al-correct' : ''} ${entry.correct === false ? 'al-incorrect' : ''}`}
            >
              <span className="al-time">{entry.timestamp}</span>
              <span className="al-message">{entry.message}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}