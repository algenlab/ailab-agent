import React, { useRef, useEffect } from 'react';

export default function ActivityLog({ entries }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current && entries.length > 0) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: entries.length > 0 ? 8 : 0 }}>
        <h3 style={{ margin: 0 }}>📋 学习日志</h3>
        {entries.length > 0 && (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {entries.length} 条记录
          </span>
        )}
      </div>
      
      {entries.length === 0 ? (
        <div className="empty-log">
          <span className="empty-log-icon">📝</span>
          <span>点击下方 <strong>"下一步 ▶"</strong> 或 <strong>"▶ 自动演示"</strong> 开始探索 DP 表格。</span>
          <span style={{ fontSize: '0.78rem', opacity: 0.7 }}>你的每一步操作都会记录在这里。</span>
        </div>
      ) : (
        <ul className="log-list" ref={listRef}>
          {entries.map((entry, i) => (
            <li key={i} className={`log-item ${entry.type === 'correct' ? 'correct-log' : entry.type === 'incorrect' ? 'incorrect-log' : ''}`}>
              <span className="log-time">{entry.time}</span>
              <span>{entry.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}