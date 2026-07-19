
import React from 'react';

export default function TreeVisualization({
  layout,
  children,
  values,
  dpTake,
  dpSkip,
  currentNode,
  nodeIds,
  compact = false,
}) {
  if (!layout || Object.keys(layout).length === 0) return null;

  // Build edge list for rendering
  const drawnEdges = [];
  for (let parent in children) {
    for (let child of children[parent]) {
      drawnEdges.push([parent, child]);
    }
  }

  const minX = Math.min(...nodeIds.map(id => layout[id]?.x || 0));
  const maxX = Math.max(...nodeIds.map(id => layout[id]?.x || 0));
  const maxY = Math.max(...nodeIds.map(id => layout[id]?.y || 0));
  const svgWidth = (maxX - minX) + 120;
  const svgHeight = maxY + 90;

  const nodeRadius = compact ? 18 : 22;
  const fontSizeId = compact ? 10 : 11;
  const fontSizeVal = compact ? 8 : 9;
  const fontSizeDP = compact ? 7 : 8;
  const dpOffsetY = compact ? 28 : 34;
  const idOffsetY = compact ? -5 : -6;
  const valOffsetY = compact ? 7 : 8;

  return (
    <div className={`tree-container ${compact ? 'tree-compact' : ''}`}>
      <svg
        viewBox={`${minX - 60} ${compact ? -5 : -10} ${svgWidth} ${svgHeight}`}
        className="tree-svg"
        style={{ width: '100%', maxWidth: compact ? '280px' : '550px', height: 'auto' }}
      >
        {/* Edges */}
        {drawnEdges.map(([p, c]) => {
          const from = layout[p];
          const to = layout[c];
          if (!from || !to) return null;
          return (
            <g key={`edge-${p}-${c}`}>
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="#94a3b8"
                strokeWidth={2.5}
                strokeLinecap="round"
              />
            </g>
          );
        })}
        {/* Nodes */}
        {nodeIds.map(id => {
          const pos = layout[id];
          if (!pos) return null;
          const isCurrent = currentNode === id;
          const takeVal = dpTake[id];
          const skipVal = dpSkip[id];
          const hasDP = takeVal !== undefined && skipVal !== undefined;

          let fillColor = '#e2e8f0';
          let strokeColor = '#94a3b8';
          let strokeWidth = 2;

          if (isCurrent) {
            fillColor = '#fbbf24';
            strokeColor = '#d97706';
            strokeWidth = 3.5;
          } else if (hasDP) {
            fillColor = '#d9f99d';
            strokeColor = '#65a30d';
            strokeWidth = 2.5;
          }

          return (
            <g key={`node-${id}`} className="tree-node">
              <circle
                cx={pos.x}
                cy={pos.y}
                r={nodeRadius}
                fill={fillColor}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              <text
                x={pos.x}
                y={pos.y + idOffsetY}
                textAnchor="middle"
                fontSize={fontSizeId}
                fontWeight="bold"
                fill="#1e293b"
              >
                {id}
              </text>
              <text
                x={pos.x}
                y={pos.y + valOffsetY}
                textAnchor="middle"
                fontSize={fontSizeVal}
                fill="#475569"
              >
                v={values[id]}
              </text>
              {hasDP && (
                <text
                  x={pos.x}
                  y={pos.y + dpOffsetY}
                  textAnchor="middle"
                  fontSize={fontSizeDP}
                  fill="#1d4ed8"
                  fontWeight="500"
                >
                  t={takeVal} s={skipVal}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
  