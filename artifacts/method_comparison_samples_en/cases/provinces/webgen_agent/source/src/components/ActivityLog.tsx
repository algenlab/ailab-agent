import React, { useRef, useEffect } from 'react';
import type { LogEntry } from '../hooks/useActivityLog';

interface ActivityLogProps {
  entries: LogEntry[];
}

const typeColors: Record<LogEntry['type'], { bg: string; border: string; dot: string; text: string }> = {
  info: { bg: '#ebf8ff', border: '#bee3f8', dot: '#3182ce', text: '#2b6cb0' },
  correct: { bg: '#f0fff4', border: '#c6f6d5', dot: '#38a169', text: '#276749' },
  incorrect: { bg: '#fff5f5', border: '#fed7d7', dot: '#e53e3e', text: '#9b2c2c' },
  hint: { bg: '#fffff0', border: '#fefcbf', dot: '#d69e2e', text: '#975a16' },
  answer: { bg: '#faf5ff', border: '#e9d8fd', dot: '#805ad5', text: '#553c9a' },
  navigation: { bg: '#f7fafc', border: '#e2e8f0', dot: '#718096', text: '#4a5568' },
  system: { bg: '#edf2f7', border: '#cbd5e0', dot: '#4a5568', text: '#2d3748' },
};

const ActivityLog: React.FC<ActivityLogProps> = ({ entries }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div style={styles.container}>
      <h3 style={styles.heading}>Learning Activity Log</h3>
      <div style={styles.list}>
        {entries.length === 0 && (
          <p style={styles.empty}>No activities recorded yet.</p>
        )}
        {entries.map((entry) => {
          const c = typeColors[entry.type];
          return (
            <div
              key={entry.id}
              style={{
                ...styles.entry,
                background: c.bg,
                borderColor: c.border,
              }}
            >
              <span style={{ ...styles.dot, background: c.dot }} />
              <div style={{ flex: 1 }}>
                <span style={{ ...styles.message, color: c.text }}>
                  {entry.message}
                </span>
                <span style={styles.time}>
                  {entry.timestamp.toLocaleTimeString()}
                </span>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '1rem',
    marginTop: '1.5rem',
    boxShadow: 'var(--shadow)',
  },
  heading: {
    fontSize: '1rem',
    fontWeight: 600,
    marginBottom: '0.75rem',
    color: 'var(--text)',
  },
  list: {
    maxHeight: '280px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  empty: {
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    fontSize: '0.875rem',
    padding: '0.5rem 0',
  },
  entry: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.5rem',
    padding: '0.5rem 0.625rem',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid transparent',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    marginTop: '0.4rem',
    flexShrink: 0,
  },
  message: {
    fontSize: '0.8rem',
    lineHeight: 1.4,
  },
  time: {
    display: 'block',
    fontSize: '0.7rem',
    color: 'var(--text-light)',
    marginTop: '0.125rem',
  },
};

export default ActivityLog;
