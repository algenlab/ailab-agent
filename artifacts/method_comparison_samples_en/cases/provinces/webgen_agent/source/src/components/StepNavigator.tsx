import React from 'react';

interface StepNavigatorProps {
  currentStep: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
  onGoTo: (step: number) => void;
  canGoPrev: boolean;
  canGoNext: boolean;
  description: string;
  provinceCount: number;
  i: number;
  j: number;
  unionPerformed: boolean;
}

const StepNavigator: React.FC<StepNavigatorProps> = ({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onGoTo,
  canGoPrev,
  canGoNext,
  description,
  provinceCount,
  i,
  j,
  unionPerformed,
}) => {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>
          Step {currentStep + 1} of {totalSteps}
        </h3>
        <div style={styles.badges}>
          <span style={styles.provBadge}>
            Provinces: <strong>{provinceCount}</strong>
          </span>
          {i >= 0 && j >= 0 && (
            <span style={styles.cellBadge}>
              Checking isConnected[{i}][{j}]
            </span>
          )}
          {unionPerformed && (
            <span style={styles.unionBadge}>Union performed</span>
          )}
        </div>
      </div>
      <p style={styles.description}>{description}</p>
      <div style={styles.controls}>
        <div style={styles.navButtons}>
          <button
            style={styles.navBtn}
            onClick={onPrev}
            disabled={!canGoPrev}
            aria-label="Go to previous step"
          >
            ← Previous
          </button>
          <span style={styles.stepIndicator}>
            {currentStep + 1} / {totalSteps}
          </span>
          <button
            style={styles.navBtn}
            onClick={onNext}
            disabled={!canGoNext}
            aria-label="Go to next step"
          >
            Next →
          </button>
        </div>
        <div style={styles.jumpWrapper}>
          <label style={styles.jumpLabel} htmlFor="step-jump">
            Go to step:
          </label>
          <select
            id="step-jump"
            value={currentStep}
            onChange={(e) => onGoTo(Number(e.target.value))}
            style={styles.jumpSelect}
          >
            {Array.from({ length: totalSteps }, (_, idx) => (
              <option key={idx} value={idx}>
                Step {idx + 1}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '1.25rem',
    boxShadow: 'var(--shadow)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  title: {
    fontSize: '1.05rem',
    fontWeight: 700,
    color: 'var(--text)',
  },
  badges: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap',
  },
  provBadge: {
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: '#ebf8ff',
    color: '#2b6cb0',
    fontSize: '0.8rem',
    fontWeight: 500,
  },
  cellBadge: {
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: '#f7fafc',
    color: '#4a5568',
    fontSize: '0.8rem',
    fontWeight: 500,
  },
  unionBadge: {
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: '#fefcbf',
    color: '#975a16',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  description: {
    fontSize: '0.9rem',
    lineHeight: 1.6,
    color: 'var(--text)',
    marginBottom: '1rem',
  },
  controls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  navButtons: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  navBtn: {
    background: 'var(--primary)',
    color: '#fff',
    fontSize: '0.85rem',
    padding: '0.5rem 1rem',
  },
  stepIndicator: {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    padding: '0 0.5rem',
  },
  jumpWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  jumpLabel: {
    fontSize: '0.8rem',
    color: 'var(--text-muted)',
  },
  jumpSelect: {
    padding: '0.35rem 0.5rem',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border)',
    fontSize: '0.8rem',
    background: '#fff',
  },
};

export default StepNavigator;
