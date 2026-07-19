import React, { useEffect, useRef } from 'react';
import './ActivityLog.css';

export default function ActivityLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  const getEntryClass = (type) => {
    switch (type) {
      case 'success': return 'log-entry--success';
      case 'error': return 'log-entry--error';
      case 'hint': return 'log-entry--hint';
      case 'answer': return 'log-entry--answer';
      case 'step': return 'log-entry--step';
      default: return '';
    }
  };

  return (
    <div className="activity-log card">
      <h2>📝 活动日志</h2>
      <div className="log-entries">
        {entries.length === 0 && (
          <p className="log-empty">暂无活动记录。开始探索算法吧！</p>
        )}
        {entries.map(entry => (
          <div key={entry.id} className={`log-entry ${getEntryClass(entry.type)}`}>
            <span className="log-time">{entry.timestamp}</span>
            <span className="log-msg">{entry.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
