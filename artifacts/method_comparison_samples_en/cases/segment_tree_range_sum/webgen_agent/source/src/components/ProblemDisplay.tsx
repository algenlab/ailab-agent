import React from 'react';

interface Props {
  nums: number[];
  query: [number, number];
  update: [number, number];
  before: number | null;
  after: number | null;
}

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-md)',
  padding: '20px',
  marginBottom: '16px',
  boxShadow: 'var(--shadow)',
};

const sectionTitle: React.CSSProperties = {
  fontSize: '0.85rem',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--accent-primary)',
  marginBottom: '8px',
};

const codeBlock: React.CSSProperties = {
  background: '#0f172a',
  border: '1px solid #334155',
  borderRadius: 'var(--radius-sm)',
  padding: '10px 14px',
  fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
  fontSize: '0.78rem',
  color: '#e2e8f0',
  lineHeight: 1.6,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  maxHeight: '220px',
  overflowY: 'auto',
};

const answerBlock: React.CSSProperties = {
  background: '#0f2b1a',
  border: '1px solid #10b981',
  borderRadius: 'var(--radius-sm)',
  padding: '14px 16px',
  fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
  fontSize: '0.95rem',
  color: '#4ade80',
  marginTop: '12px',
};

const explanationStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#94a3b8',
  marginTop: '10px',
  lineHeight: 1.6,
};

const placeholderStyle: React.CSSProperties = {
  marginTop: '12px',
  padding: '14px 16px',
  background: '#1e293b',
  border: '1px dashed #475569',
  borderRadius: 'var(--radius-sm)',
  color: '#64748b',
  fontSize: '0.85rem',
  textAlign: 'center',
  minHeight: '60px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const columnStyle: React.CSSProperties = {
  flex: '1 1 300px',
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
};

export default function ProblemDisplay({ nums, query, update, before, after }: Props) {
  const inputJson = JSON.stringify({ nums, query, update }, null, 2);
  const answerJson =
    before !== null && after !== null
      ? JSON.stringify({ before, after })
      : null;

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'stretch' }}>
        <div style={columnStyle}>
          <div style={sectionTitle}>📥 Problem Input</div>
          <pre style={codeBlock}>{inputJson}</pre>
          <div style={explanationStyle}>
            The <code>nums</code> array holds parcel weights per hour. Query the
            total for <strong>[{query[0]}, {query[1]}]</strong>, apply{' '}
            <strong>update=[{update[0]}, {update[1]}]</strong>, then re-query.
          </div>
        </div>
        <div style={columnStyle}>
          <div style={sectionTitle}>📤 Expected Output</div>
          <pre style={{ ...codeBlock, maxHeight: '120px' }}>
            {'{"after": 12, "before": 10}'}
          </pre>
          {answerJson ? (
            <div style={answerBlock}>
              ✅ Your computed result: <strong>{answerJson}</strong>
            </div>
          ) : (
            <div style={placeholderStyle}>
              Use the controls below to build the tree, query, update, and
              re-query. Your computed result will appear here.
            </div>
          )}
          <div style={explanationStyle}>
            <strong>Before:</strong> 1 + 4 + 5 = <strong>10</strong>
              |  
            <strong>After:</strong> 1 + 6 + 5 = <strong>12</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
