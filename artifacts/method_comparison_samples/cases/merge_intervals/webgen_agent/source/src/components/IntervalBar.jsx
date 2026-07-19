import React from 'react';

export default function IntervalBar({
  allValues,
  range,
  toPercent,
  merged,
  current,
  future,
  stepIndex,
}) {
  if (range <= 0) return null;

  const segments = [];

  // Add merged intervals (green)
  if (merged) {
    merged.forEach(([a, b], i) => {
      segments.push({
        key: `merged-${i}`,
        left: toPercent(a),
        width: Math.max(2, toPercent(b) - toPercent(a)),
        label: `[${a},${b}]`,
        cls: i === merged.length - 1 && stepIndex >= 0 ? 'seg-merged' : 'seg-inactive-merged',
      });
    });
  }

  // Add current interval being processed (orange)
  if (current) {
    const isAlreadyInMerged =
      merged &&
      merged.some(([a, b]) => a === current[0] && b === current[1]);
    if (!isAlreadyInMerged) {
      segments.push({
        key: 'current',
        left: toPercent(current[0]),
        width: Math.max(2, toPercent(current[1]) - toPercent(current[0])),
        label: `[${current[0]},${current[1]}]`,
        cls: 'seg-current',
      });
    }
  }

  // Add future intervals (grey)
  if (future) {
    future.forEach(([a, b], i) => {
      segments.push({
        key: `future-${i}`,
        left: toPercent(a),
        width: Math.max(2, toPercent(b) - toPercent(a)),
        label: `[${a},${b}]`,
        cls: 'seg-future',
      });
    });
  }

  // Axis ticks
  const tickCount = 6;
  const ticks = [];
  for (let i = 0; i <= tickCount; i++) {
    const val = Math.round(allValues[0] + (range * i) / tickCount);
    const pct = (i / tickCount) * 100;
    ticks.push({ val, pct });
  }

  return (
    <div style={{ position: 'relative', margin: '10px 0 6px' }}>
      <div className="interval-bar">
        {segments.map((seg) => (
          <div
            key={seg.key}
            className={`interval-seg ${seg.cls}`}
            style={{
              left: `${seg.left}%`,
              width: `${seg.width}%`,
            }}
            title={seg.label}
          >
            {seg.label}
          </div>
        ))}
      </div>
      {/* Axis */}
      <div
        style={{
          position: 'relative',
          height: 18,
          marginTop: 2,
        }}
      >
        {ticks.map((t, i) => (
          <span
            key={i}
            style={{
              position: 'absolute',
              left: `${t.pct}%`,
              transform: 'translateX(-50%)',
              fontSize: '0.65rem',
              color: '#94a3b8',
              fontFamily: 'monospace',
            }}
          >
            {t.val}
          </span>
        ))}
      </div>
    </div>
  );
}
