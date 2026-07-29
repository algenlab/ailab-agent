import React from 'react';

export default function DPTable({
  dpSnapshot,
  m,
  n,
  currentCell,
  aboveVal,
  leftVal,
  currentValue,
}) {
  if (!dpSnapshot) {
    return <div className="dp-table-empty">No data to display yet.</div>;
  }

  const [ci, cj] = currentCell || [-1, -1];

  return (
    <div className="dp-table-wrapper">
      <div
        className="dp-grid"
        style={{
          gridTemplateColumns: `repeat(${n}, 1fr)`,
          gridTemplateRows: `repeat(${m}, 1fr)`,
        }}
      >
        {dpSnapshot.map((row, i) =>
          row.map((val, j) => {
            const isCurrent = i === ci && j === cj;
            const isSourceAbove = isCurrent && i > 0 && i - 1 === ci - 1 && j === cj;
            const isSourceLeft = isCurrent && j > 0 && i === ci && j - 1 === cj - 1;
            const isSource =
              (i === ci - 1 && j === cj && ci > 0) ||
              (i === ci && j === cj - 1 && cj > 0);
            const isBaseRowCol = i === 0 || j === 0;
            const isDestination = i === m - 1 && j === n - 1;
            const isComputed = val !== null;

            let cellClass = 'dp-cell';
            if (isCurrent) cellClass += ' dp-cell--current';
            else if (isSource) cellClass += ' dp-cell--source';
            else if (isComputed && isBaseRowCol) cellClass += ' dp-cell--base';
            else if (isComputed) cellClass += ' dp-cell--computed';
            else cellClass += ' dp-cell--empty';

            if (isDestination && isComputed) cellClass += ' dp-cell--destination';

            return (
              <div key={`${i}-${j}`} className={cellClass} title={`dp[${i}][${j}]`}>
                <span className="dp-cell-coord">({i},{j})</span>
                <span className="dp-cell-value">
                  {isComputed ? val : '—'}
                </span>
              </div>
            );
          })
        )}
      </div>

      {currentCell && currentValue !== null && (
        <div className="dp-recurrence">
          <p>
            <strong>Computing dp[{ci}][{cj}]:</strong>
            {' '}
            {ci === 0 && cj === 0 ? (
              <span>Starting cell — base value is <code>1</code>.</span>
            ) : ci === 0 ? (
              <span>
                First row — only one path (all right):{' '}
                <code>dp[0][{cj}] = 1</code>
              </span>
            ) : cj === 0 ? (
              <span>
                First column — only one path (all down):{' '}
                <code>dp[{ci}][0] = 1</code>
              </span>
            ) : (
              <span>
                <code>
                  dp[{ci}][{cj}] = dp[{ci - 1}][{cj}] + dp[{ci}][{cj - 1}]
                </code>
                <br />
                <code>
                  = {aboveVal} + {leftVal} = <strong>{currentValue}</strong>
                </code>
              </span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
