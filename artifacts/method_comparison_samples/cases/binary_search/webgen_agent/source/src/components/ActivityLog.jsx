import React, { useEffect, useRef } from 'react';
import './ActivityLog.css';

const typeConfig = {
  navigation: { icon: '🔹', label: '导航' },
  action: { icon: '🔸', label: '操作' },
  hint: { icon: '💡', label: '提示' },
  correct: { icon: '✅', label: '正确' },
  incorrect: { icon: '❌', label: '需改进' }
};

export default function ActivityLog({ entries }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current && entries.length > 0) {
      listRef.current.scrollTop = 0;
    }
  }, [entries.length]);

  return (
    <div className="activity-log">
      <h3 className="section-title">📜 活动日志</h3>
      <div className="log-list" ref={listRef}>
        {entries.length === 0 && (
          <p className="log-empty">暂无活动记录。开始探索算法吧！</p>
        )}
        {entries.map(entry => {
          const config = typeConfig[entry.type] || typeConfig.navigation;
          return (
            <div key={entry.id} className={`log-entry log-${entry.type}`}>
              <span className="log-icon">{config.icon}</span>
              <span className="log-time">{entry.timestamp}</span>
              <span className="log-message">{entry.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
