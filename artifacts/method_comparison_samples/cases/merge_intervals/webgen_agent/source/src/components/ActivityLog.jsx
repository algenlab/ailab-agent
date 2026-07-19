import React, { useRef, useEffect } from 'react';

export default function ActivityLog({ logs }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="card activity-log full-width">
      <div className="card-header">
        <span className="icon">📝</span>
        <h2>学习活动日志</h2>
      </div>
      <div className="log-list">
        {logs.length === 0 && (
          <div style={{ color: '#94a3b8', fontSize: '0.82rem' }}>暂无活动记录。</div>
        )}
        {logs.map((log, i) => (
          <div className="log-item" key={i}>
            <span className="log-time">{log.time}</span>
            <span className="log-icon">{log.icon}</span>
            <span className="log-msg">{log.msg}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
