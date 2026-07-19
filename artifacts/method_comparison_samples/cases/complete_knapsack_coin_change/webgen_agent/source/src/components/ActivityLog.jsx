import React, { useRef, useEffect } from 'react'

export default function ActivityLog({ entries }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries.length])

  const getIcon = (type) => {
    switch (type) {
      case 'correct': return '✅'
      case 'incorrect': return '❌'
      case 'hint': return '💡'
      case 'showAnswer': return '👁️'
      case 'navigation': return '🔍'
      case 'system': return '🤖'
      default: return '📌'
    }
  }

  return (
    <div style={styles.card}>
      <h2 style={styles.sectionTitle}>📝 学习活动记录</h2>
      <div style={styles.logContainer}>
        {entries.length === 0 && (
          <p style={styles.empty}>暂无活动记录。开始探索吧！</p>
        )}
        {entries.map(entry => (
          <div key={entry.id} style={styles.entry}>
            <span style={styles.icon}>{getIcon(entry.type)}</span>
            <span style={styles.message}>{entry.message}</span>
            <span style={styles.time}>
              {entry.time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

const styles = {
  card: {
    background: '#fff',
    borderRadius: '16px',
    padding: '24px 32px',
    boxShadow: '0 2px 16px rgba(0,0,0,0.06)',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#1a202c',
    marginBottom: '12px',
  },
  logContainer: {
    maxHeight: '220px',
    overflowY: 'auto',
    paddingRight: '4px',
  },
  empty: {
    color: '#a0aec0',
    fontSize: '14px',
    fontStyle: 'italic',
  },
  entry: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
    padding: '7px 0',
    borderBottom: '1px solid #f7fafc',
    fontSize: '13px',
  },
  icon: {
    flexShrink: 0,
    marginTop: '1px',
  },
  message: {
    flex: 1,
    color: '#4a5568',
    lineHeight: 1.5,
  },
  time: {
    flexShrink: 0,
    color: '#a0aec0',
    fontSize: '11px',
    fontFamily: "'SF Mono', 'Fira Code', monospace",
  },
}