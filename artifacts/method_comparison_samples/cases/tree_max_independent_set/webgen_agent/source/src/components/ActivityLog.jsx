
import React, { useEffect, useRef } from 'react';

export default function ActivityLog({ log }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [log]);

  return (
    <section className="activity-log-section">
      <h3>📝 活动日志</h3>
      <ul ref={listRef}>
        {log.length === 0 && <li className="log-empty">尚无活动。点击"下一步"开始算法遍历。</li>}
        {log.map((entry, i) => (
          <li key={i} className={`log-entry ${entry.type || ''}`}>
            <span className="log-time">{i + 1}.</span> {entry.message}
          </li>
        ))}
      </ul>
    </section>
  );
}
  