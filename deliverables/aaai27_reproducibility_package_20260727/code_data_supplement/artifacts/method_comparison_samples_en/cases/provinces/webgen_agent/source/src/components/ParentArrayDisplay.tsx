import React from 'react';

interface ParentArrayDisplayProps {
  parent: number[];
  changedIndex?: number;
  label?: string;
}

const ParentArrayDisplay: React.FC<ParentArrayDisplayProps> = ({
  parent,
  changedIndex = -1,
  label,
}) => {
  return (
    <div style={styles.wrapper}>
      {label && <h3 style={styles.label}>{label}</h3>}
      <div style={styles.arrayContainer}>
        {parent.map((val, idx) => {
          const isChanged = idx === changedIndex;
          const isRoot = val === idx;
          return (
            <div
              key={idx}
              style={{
                ...styles.element,
                ...(isChanged ? styles.changed : {}),
                ...(isRoot ? styles.root : {}),
              }}
              aria-label={`parent[${idx}] = ${val}`}
            >
              <span style={styles.idx}>{idx}</span>
              <span style={styles.val}>{val}</span>
              <span style={styles.idxLabel}>p[{idx}]={val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  label: {
    fontSize: '0.875rem',
    fontWeight: 600,
    marginBottom: '0.5rem',
    color: 'var(--text)',
  },
  arrayContainer: {
    display: 'flex',
    gap: '0.75rem',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  element: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: '56px',
    padding: '0.5rem 0.25rem',
    borderRadius: 'var(--radius-sm)',
    border: '2px solid var(--border)',
    background: '#f7fafc',
    transition: 'background 0.2s, border-color 0.2s, transform 0.15s',
  },
  changed: {
    background: '#fefcbf',
    borderColor: '#ecc94b',
    transform: 'scale(1.1)',
    boxShadow: '0 0 8px rgba(236, 201, 75, 0.5)',
  },
  root: {
    borderColor: '#38a169',
    background: '#f0fff4',
  },
  idx: {
    fontSize: '0.65rem',
    color: 'var(--text-muted)',
    fontWeight: 600,
  },
  val: {
    fontSize: '1.2rem',
    fontWeight: 700,
    color: 'var(--text)',
  },
  idxLabel: {
    fontSize: '0.6rem',
    color: 'var(--text-light)',
    marginTop: '2px',
  },
};

export default ParentArrayDisplay;
