import React, { useRef, useEffect } from 'react';

const INF = Infinity;

function formatVal(v) {
  if (!isFinite(v)) return '∞';
  return v;
}

export default function DpTable({
  dp,
  highlightIndex,
  referenceIndex,
  coin,
  capacity,
  changed,
  amount
}) {
  const highlightRef = useRef(null);

  useEffect(() => {
    if (highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [highlightIndex]);

  return (
    <div className="dp-table-container">
      <h3 className="section-title">DP Array State</h3>
      <div className="dp-table-scroll">
        <div className="dp-table">
          <div className="dp-header-row">
            <div className="dp-header-cell">Index c</div>
            {dp.map((_, i) => (
              <div
                key={i}
                className={`dp-header-cell ${i === highlightIndex ? 'header-highlight' : ''} ${i === 0 ? 'header-base' : ''}`}
              >
                {i}
              </div>
            ))}
          </div>
          <div className="dp-values-row">
            <div className="dp-header-cell">dp[c]</div>
            {dp.map((val, i) => {
              let cellClass = 'dp-cell';
              if (i === 0) cellClass += ' cell-base';
              if (i === highlightIndex && changed) cellClass += ' cell-updated';
              else if (i === highlightIndex && !changed) cellClass += ' cell-unchanged';
              else if (i === referenceIndex && referenceIndex !== null) cellClass += ' cell-reference';
              else if (isFinite(val)) cellClass += ' cell-computed';
              else cellClass += ' cell-inf';

              return (
                <div
                  key={i}
                  className={cellClass}
                  ref={i === highlightIndex ? highlightRef : null}
                  title={`dp[${i}] = ${formatVal(val)}`}
                >
                  {formatVal(val)}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="dp-legend">
        <span className="legend-item"><span className="legend-swatch swatch-base"></span> Base (dp[0])</span>
        <span className="legend-item"><span className="legend-swatch swatch-updated"></span> Updated</span>
        <span className="legend-item"><span className="legend-swatch swatch-unchanged"></span> No Change</span>
        <span className="legend-item"><span className="legend-swatch swatch-reference"></span> Reference dp[c-coin]</span>
        <span className="legend-item"><span className="legend-swatch swatch-computed"></span> Computed</span>
        <span className="legend-item"><span className="legend-swatch swatch-inf"></span> Unreachable (∞)</span>
      </div>
    </div>
  );
}
