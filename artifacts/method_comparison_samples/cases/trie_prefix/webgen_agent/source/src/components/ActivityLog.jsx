import React from 'react';

export default function ActivityLog({ entries }) {
  return (
    <div className="card">
      <div className="card-header">📜 学习活动记录</div>
      {entries.length === 0 ? (
        <div className="log-empty">暂无记录。开始导航步骤或回答问题吧！</div>
      ) : (
        <ul className="log-list">
          {entries.map((entry) => (
            <li key={entry.id} className={`log-entry ${entry.type}`}>
              <span>{entry.message}</span>
              <span className="log-time">{entry.time}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
