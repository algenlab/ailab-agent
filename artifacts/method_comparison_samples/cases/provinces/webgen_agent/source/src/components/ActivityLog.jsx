import React, { useEffect, useRef } from 'react';
import './ActivityLog.css';

export default function ActivityLog({ entries }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries.length]);

  function formatTime(ts) {
    const d = new Date(ts);
    return d.toLocaleTimeString('zh-CN', { hour12: false });
  }

  return (
    <div className="card activity-log">
      <div className="card-header">
        <span>📜</span> 学习活动日志
        <span className="log-count">{entries.length}</span>
      </div>

      <div className="log-entries">
        {entries.length === 0 && (
          <p className="log-empty">暂无活动记录。开始探索算法吧！</p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className={`log-entry log-${entry.type}`}>
            <span className="log-time">{formatTime(entry.timestamp)}</span>
            <span className="log-message">{entry.message}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}