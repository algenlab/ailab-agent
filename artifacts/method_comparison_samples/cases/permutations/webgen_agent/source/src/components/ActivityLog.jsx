import React, { useRef, useEffect } from 'react';

export default function ActivityLog({ entries }) {
  const logEndRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [entries.length]);

  const dotClassMap = {
    nav: 'log-dot-nav',
    correct: 'log-dot-correct',
    incorrect: 'log-dot-incorrect',
    hint: 'log-dot-hint',
    answer: 'log-dot-answer',
    info: 'log-dot-info',
  };

  const typeLabelMap = {
    nav: '导航',
    correct: '正确',
    incorrect: '错误',
    hint: '提示',
    answer: '答案',
    info: '信息',
  };

  return (
    <div className="card area-log">
      <div className="card-header">
        <div className="icon icon-red">📝</div>
        <h2>活动日志</h2>
        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          {entries.length} 条记录
        </span>
      </div>
      <div className="log-container">
        {entries.length === 0 ? (
          <div className="log-empty">尚无活动记录。开始浏览算法步骤或回答问题吧！</div>
        ) : (
          entries.map((entry, i) => (
            <div key={i} className="log-entry">
              <span className="log-time">{entry.time}</span>
              <span className={`log-dot ${dotClassMap[entry.type] || 'log-dot-info'}`} />
              <span className="log-msg">
                <strong>[{typeLabelMap[entry.type] || entry.type}]</strong> {entry.message}
              </span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
