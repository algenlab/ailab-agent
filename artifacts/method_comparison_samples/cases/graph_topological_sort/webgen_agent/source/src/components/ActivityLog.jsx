import React, { useEffect, useRef } from 'react';

export function ActivityLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="card full-width">
      <h2>📝 学习活动日志</h2>
      <div className="activity-log">
        {entries.length === 0 && (
          <div className="empty-state">
            <span className="empty-state-icon">📭</span>
            <span className="empty-state-text">尚无活动记录</span>
            <span className="empty-state-hint">尝试点击"下一步"或回答检测题，活动将在此显示</span>
          </div>
        )}
        {entries.map((e, i) => (
          <div key={i} className={`log-entry ${e.type}`}>
            <span className="log-time">{e.time}</span>
            <span>{e.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
