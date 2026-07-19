import React from 'react';

interface Props {
  currentStep: string;
  onBuild: () => void;
  onQuery: () => void;
  onUpdate: () => void;
  onReQuery: () => void;
  onReset: () => void;
}

const wrapperStyle: React.CSSProperties = {
  display: 'flex',
  gap: '10px',
  flexWrap: 'wrap',
  marginBottom: '16px',
  alignItems: 'center',
};

const btnBase: React.CSSProperties = {
  padding: '10px 20px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid transparent',
  fontWeight: 600,
  fontSize: '0.9rem',
  transition: 'all 0.15s ease',
  cursor: 'pointer',
};

const primaryBtn: React.CSSProperties = {
  ...btnBase,
  background: '#3b82f6',
  color: '#fff',
  borderColor: '#3b82f6',
};

const successBtn: React.CSSProperties = {
  ...btnBase,
  background: '#10b981',
  color: '#fff',
  borderColor: '#10b981',
};

const warningBtn: React.CSSProperties = {
  ...btnBase,
  background: '#f59e0b',
  color: '#0f172a',
  borderColor: '#f59e0b',
};

const outlineBtn: React.CSSProperties = {
  ...btnBase,
  background: 'transparent',
  color: '#cbd5e1',
  borderColor: '#475569',
};

const stepIndicator: React.CSSProperties = {
  fontSize: '0.85rem',
  color: '#94a3b8',
  marginLeft: 'auto',
  padding: '8px 14px',
  background: '#1e293b',
  borderRadius: '20px',
  border: '1px solid #334155',
  whiteSpace: 'nowrap',
};

const disabledBtn: React.CSSProperties = {
  ...btnBase,
  background: '#1e293b',
  color: '#475569',
  borderColor: '#334155',
  cursor: 'not-allowed',
  opacity: 0.5,
};

function isDisabled(step: string, targetStep: string): boolean {
  const order = ['initial', 'built', 'query', 'update', 'complete'];
  const currentIdx = order.indexOf(step);
  const targetIdx = order.indexOf(targetStep);
  return currentIdx < targetIdx - 1 || step === 'initial';
}

function buttonStyle(
  baseStyle: React.CSSProperties,
  disabled: boolean
): React.CSSProperties {
  if (disabled) {
    return { ...baseStyle, ...disabledBtn };
  }
  return baseStyle;
}

export default function Controls({
  currentStep,
  onBuild,
  onQuery,
  onUpdate,
  onReQuery,
  onReset,
}: Props) {
  const stepLabels: Record<string, string> = {
    initial: 'Step 0: Ready',
    built: 'Step 1: Tree Built',
    query: 'Step 2: Range Queried',
    update: 'Step 3: Point Updated',
    complete: 'Step 4: Complete',
  };

  return (
    <div style={wrapperStyle}>
      <button
        style={buttonStyle(primaryBtn, currentStep !== 'initial')}
        onClick={onBuild}
        disabled={currentStep !== 'initial'}
        aria-label="Build the segment tree"
      >
        🔨 Build Tree
      </button>
      <button
        style={buttonStyle(
          successBtn,
          isDisabled(currentStep, 'query') && currentStep !== 'built'
        )}
        onClick={onQuery}
        disabled={
          isDisabled(currentStep, 'query') && currentStep !== 'built'
        }
        aria-label="Query the range"
      >
        🔍 Query Range
      </button>
      <button
        style={buttonStyle(warningBtn, currentStep !== 'query')}
        onClick={onUpdate}
        disabled={currentStep !== 'query'}
        aria-label="Apply point update"
      >
        ✏️ Apply Update
      </button>
      <button
        style={buttonStyle(primaryBtn, currentStep !== 'update')}
        onClick={onReQuery}
        disabled={currentStep !== 'update'}
        aria-label="Re-query after update"
      >
        🔍 Re-query
      </button>
      <button
        style={outlineBtn}
        onClick={onReset}
        aria-label="Reset the session"
      >
        ↺ Reset
      </button>
      <span style={stepIndicator}>
        {stepLabels[currentStep] || currentStep}
      </span>
    </div>
  );
}
