import React, { useEffect, useRef } from 'react';

const ICON_MAP = {
  system: '\u2139\uFE0F',
  navigate: '\uD83D\uDCCD',
  correct: '\u2705',
  incorrect: '\u274C',
  hint: '\uD83D\uDCA1',
  reveal: '\uD83D\uDC41',
};

export default function ActivityLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="activity-log">
      <div className="activity-log-title">Activity Log</div>
      {entries.map((entry) => (
        <div className="activity-entry" key={entry.id}>
          <span className="activity-time">{entry.time}</span>
          <span className="activity-icon">{ICON_MAP[entry.type] || '\u2022'}</span>
          <span className="activity-message">{entry.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}