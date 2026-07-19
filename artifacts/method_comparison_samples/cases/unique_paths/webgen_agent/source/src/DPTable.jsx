import React, { useState, useEffect, useCallback } from 'react';

function getCellClass(i, j, currentI, currentJ, deps, isEdge, isComputed) {
  if (i === currentI && j === currentJ) return 'dp-cell dp-cell-current';
  if (deps.some(d => d.i === i && d.j === j)) return 'dp-cell dp-cell-dependency';
  if (isEdge && isComputed) return 'dp-cell dp-cell-edge';
  if (isComputed) return 'dp-cell dp-cell-computed';
  return 'dp-cell dp-cell-default';
}

function getCellSize() {
  if (typeof window === 'undefined') return 52;
  if (window.innerWidth <= 480) return 34;
  if (window.innerWidth <= 768) return 40;
  return 52;
}

function getLabelSize() {
  if (typeof window === 'undefined') return 30;
  if (window.innerWidth <= 480) return 22;
  if (window.innerWidth <= 768) return 26;
  return 30;
}

function getGap() {
  if (typeof window === 'undefined') return 3;
  if (window.innerWidth <= 480) return 1;
  if (window.innerWidth <= 768) return 2;
  return 3;
}

export default function DPTable({ m, n, steps, currentStep, dp }) {
  const [cellSize, setCellSize] = useState(getCellSize());
  const [labelSize, setLabelSize] = useState(getLabelSize());
  const [gap, setGap] = useState(getGap());

  const updateSizes = useCallback(() => {
    setCellSize(getCellSize());
    setLabelSize(getLabelSize());
    setGap(getGap());
  }, []);

  useEffect(() => {
    updateSizes();
    window.addEventListener('resize', updateSizes);
    return () => window.removeEventListener('resize', updateSizes);
  }, [updateSizes]);

  if (!steps || steps.length === 0) return null;

  const current = steps[Math.min(currentStep, steps.length - 1)];
  const currentI = current.i;
  const currentJ = current.j;
  const deps = current.dependencies || [];
  const maxStep = Math.min(currentStep, steps.length - 1);

  const computedSet = new Set();
  for (let s = 0; s <= maxStep; s++) {
    computedSet.add(`${steps[s].i},${steps[s].j}`);
  }

  const gridStyle = {
    gridTemplateColumns: `${labelSize}px repeat(${n}, ${cellSize}px)`,
    gridTemplateRows: `${labelSize}px repeat(${m}, ${cellSize}px)`,
    gap: `${gap}px`
  };

  return (
    <div className="dp-grid-wrapper">
      <div className="dp-grid" style={gridStyle}>
        {/* Top-left corner */}
        <div className="col-label"></div>
        {/* Column headers */}
        {Array.from({ length: n }, (_, j) => (
          <div key={`col-${j}`} className="col-label">j={j}</div>
        ))}
        {/* Rows */}
        {Array.from({ length: m }, (_, i) => (
          <React.Fragment key={`row-${i}`}>
            <div className="row-label">i={i}</div>
            {Array.from({ length: n }, (_, j) => {
              const isComputed = computedSet.has(`${i},${j}`);
              const cellClass = getCellClass(i, j, currentI, currentJ, deps, i === 0 || j === 0, isComputed);
              const value = isComputed ? (dp[i]?.[j] ?? '') : '';
              return (
                <div key={`${i}-${j}`} className={cellClass}>
                  {value || <span style={{ opacity: 0.3, fontSize: '0.7rem' }}>·</span>}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}