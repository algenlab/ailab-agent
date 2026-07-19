import React, { useRef, useEffect } from 'react';

export default function ActivityLog({ entries }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <div className="activity-log-panel">
      <h3>📋 学习活动日志</h3>
      <div className="activity-entries" ref={logRef}>
        {entries.length === 0 && (
          <div className="log-empty">暂无活动记录。开始探索算法步骤或回答问题吧！</div>
        )}
        {entries.map((entry, i) => (
          <div key={i} className={`activity-entry activity-${entry.type || 'info'}`}>
            <span className="activity-time">{entry.timestamp}</span>
            <span className="activity-icon">
              {entry.type === 'step' ? '🔍' :
               entry.type === 'answer-correct' ? '✅' :
               entry.type === 'answer-incorrect' ? '❌' :
               entry.type === 'hint' ? '💡' :
               entry.type === 'show-answer' ? '👁' : 'ℹ️'}
            </span>
            <span className="activity-text">{entry.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}