import React, { useRef, useEffect } from 'react';
import { ActivityEntry } from '../types';

interface Props {
  entries: ActivityEntry[];
}

const ActivityLog: React.FC<Props> = ({ entries }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="activity-log">
      {entries.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', padding: '8px 0' }}>
          暂无活动记录。开始操作算法步骤或回答问题来查看记录。
        </div>
      )}
      {entries.map((entry) => (
        <div key={entry.id} className="activity-entry">
          <span className="ae-time">{entry.timestamp}</span>
          <span className={`ae-badge ${entry.type}`}>
            {entry.type === 'navigation'
              ? '导航'
              : entry.type === 'answer'
              ? '答题'
              : entry.type === 'hint'
              ? '提示'
              : entry.type === 'reveal'
              ? '答案'
              : '系统'}
          </span>
          <span className="ae-detail">
            <strong>{entry.action}</strong> — {entry.detail}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default ActivityLog;
