import React, { useEffect, useRef } from 'react';

interface Props {
  entries: string[];
}

const logContainerStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-md)',
  padding: '20px',
  boxShadow: 'var(--shadow)',
  minHeight: '320px',
  maxHeight: '420px',
  display: 'flex',
  flexDirection: 'column',
};

const logListStyle: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  fontSize: '0.8rem',
  lineHeight: 1.7,
  color: '#94a3b8',
  listStyle: 'none',
  padding: 0,
  margin: 0,
};

const logItemStyle: React.CSSProperties = {
  padding: '6px 10px',
  borderBottom: '1px solid #1e293b',
  fontFamily: '"Fira Code", "Cascadia Code", monospace',
  fontSize: '0.78rem',
};

const emptyStyle: React.CSSProperties = {
  color: '#475569',
  textAlign: 'center',
  padding: '40px 0',
  fontStyle: 'italic',
};

export default function ActivityLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div style={logContainerStyle}>
      <h3
        style={{
          fontSize: '1rem',
          fontWeight: 700,
          color: '#e2e8f0',
          marginBottom: '12px',
        }}
      >
        📜 Activity Log
      </h3>
      {entries.length === 0 ? (
        <div style={emptyStyle}>
          No activity yet. Start by building the tree.
        </div>
      ) : (
        <ul style={logListStyle}>
          {entries.map((entry, idx) => (
            <li key={idx} style={logItemStyle}>
              {entry}
            </li>
          ))}
          <div ref={bottomRef} />
        </ul>
      )}
    </div>
  );
}
