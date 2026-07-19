import React from 'react';

interface AnswerBadgeProps {
  answer: number;
}

const AnswerBadge: React.FC<AnswerBadgeProps> = ({ answer }) => {
  return (
    <div style={styles.badge}>
      <span style={styles.label}>Final Answer</span>
      <span style={styles.value}>{answer}</span>
      <span style={styles.unit}>province{answer !== 1 ? 's' : ''}</span>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.75rem',
    background: 'linear-gradient(135deg, #ebf8ff 0%, #e9d8fd 100%)',
    border: '2px solid #90cdf4',
    borderRadius: 'var(--radius)',
    padding: '0.75rem 1.25rem',
    boxShadow: 'var(--shadow)',
  },
  label: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  value: {
    fontSize: '2rem',
    fontWeight: 800,
    color: 'var(--primary)',
    lineHeight: 1,
  },
  unit: {
    fontSize: '0.85rem',
    color: 'var(--text-muted)',
  },
};

export default AnswerBadge;
