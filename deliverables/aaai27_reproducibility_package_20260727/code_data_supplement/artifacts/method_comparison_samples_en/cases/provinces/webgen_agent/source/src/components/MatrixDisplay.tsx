import React from 'react';

interface MatrixDisplayProps {
  matrix: number[][];
  highlightI?: number;
  highlightJ?: number;
  label?: string;
}

const MatrixDisplay: React.FC<MatrixDisplayProps> = ({
  matrix,
  highlightI = -1,
  highlightJ = -1,
  label,
}) => {
  const n = matrix.length;

  return (
    <div style={styles.wrapper}>
      {label && <h3 style={styles.label}>{label}</h3>}
      <div style={styles.matrixContainer}>
        {/* Column indices */}
        <div style={styles.headerRow}>
          <div style={styles.cornerCell} />
          {Array.from({ length: n }, (_, j) => (
            <div key={`col-${j}`} style={styles.indexCell}>
              {j}
            </div>
          ))}
        </div>
        {matrix.map((row, i) => (
          <div key={`row-${i}`} style={styles.row}>
            <div style={styles.indexCell}>{i}</div>
            {row.map((val, j) => {
              const isHighlighted =
                (i === highlightI && j === highlightJ) ||
                (i === highlightJ && j === highlightI);
              const isDiagonal = i === j;
              return (
                <div
                  key={`cell-${i}-${j}`}
                  style={{
                    ...styles.cell,
                    ...(isHighlighted ? styles.cellHighlighted : {}),
                    ...(isDiagonal ? styles.cellDiagonal : {}),
                    ...(val === 1 ? styles.cellOne : styles.cellZero),
                  }}
                  aria-label={`isConnected[${i}][${j}] = ${val}`}
                >
                  {val}
                </div>
              );
            })}
          </div>
        ))}
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
    textAlign: 'center' as const,
  },
  matrixContainer: {
    display: 'inline-flex',
    flexDirection: 'column',
    border: '2px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    overflow: 'hidden',
  },
  headerRow: {
    display: 'flex',
    flexDirection: 'row',
    background: '#edf2f7',
  },
  cornerCell: {
    width: '28px',
    height: '28px',
  },
  indexCell: {
    width: '40px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.7rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    background: '#edf2f7',
  },
  row: {
    display: 'flex',
    flexDirection: 'row',
  },
  cell: {
    width: '40px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.85rem',
    fontWeight: 600,
    border: '1px solid #e2e8f0',
    transition: 'background 0.2s, transform 0.15s',
  },
  cellDiagonal: {
    background: '#ebf8ff',
    color: '#2b6cb0',
  },
  cellOne: {
    color: '#2f855a',
  },
  cellZero: {
    color: '#a0aec0',
  },
  cellHighlighted: {
    background: '#fefcbf',
    border: '2px solid #ecc94b',
    transform: 'scale(1.05)',
    zIndex: 1,
    boxShadow: '0 0 6px rgba(236, 201, 75, 0.5)',
  },
};

export default MatrixDisplay;
