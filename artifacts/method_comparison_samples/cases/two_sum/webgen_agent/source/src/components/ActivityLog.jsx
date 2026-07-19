import { useEffect, useRef } from 'react'

const iconMap = {
  nav: '📍',
  correct: '✅',
  incorrect: '❌',
  hint: '💡',
  answer: '👁️',
  info: '📋',
  checkpoint: '🔮'
}

const logClassMap = {
  correct: 'log-correct',
  incorrect: 'log-incorrect',
  hint: 'log-hint'
}

export default function ActivityLog({ entries }) {
  const listRef = useRef(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [entries])

  return (
    <section className="activity-log card">
      <div className="card-header">
        <span className="icon">📜</span> 学习活动日志
      </div>
      {entries.length === 0 ? (
        <div className="log-empty">暂无活动记录。开始探索算法吧！</div>
      ) : (
        <ul className="log-list" ref={listRef}>
          {entries.map((entry) => (
            <li key={entry.id} className={`log-entry ${logClassMap[entry.icon] || ''}`}>
              <span className="log-icon">{iconMap[entry.icon] || '📌'}</span>
              <span className="log-time">{entry.time}</span>
              <span className="log-text">{entry.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}