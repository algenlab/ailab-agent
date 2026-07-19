import React, { useRef, useEffect } from 'react';

export default function ActivityLog({ entries }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries.length]);

  if (entries.length === 0) {
    return (
      <div className="log-container">
        <div className="log-empty">
          📭 暂无活动记录。尝试点击"下一步"或"开始测验"来开始学习。
        </div>
      </div>
    );
  }

  return (
    <div className="log-container">
      {entries.map((entry) => (
        <div className="log-entry" key={entry.id}>
          <span className="log-time">{entry.time}</span>
          <span className="log-icon">{entry.icon}</span>
          <span className="log-msg">{entry.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}