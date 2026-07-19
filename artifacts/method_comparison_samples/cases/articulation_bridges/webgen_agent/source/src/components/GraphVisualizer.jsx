import React, { useState } from 'react';
import { NODE_POSITIONS } from '../utils/algorithm';

export default function GraphVisualizer({
  graph,
  currentNode,
  visitedNodes,
  bridges,
  articulationPoints,
  activeEdge,
  exploringEdge,
  dfn,
  low,
  highlightNodes
}) {
  const [hoveredNode, setHoveredNode] = useState(null);

  // Build edge list (deduplicated)
  const edges = [];
  const seen = new Set();
  for (const u of Object.keys(graph)) {
    for (const v of graph[u]) {
      const key = [u, v].sort().join('-');
      if (!seen.has(key)) {
        seen.add(key);
        edges.push([u, v]);
      }
    }
  }

  function getEdgeStyle(u, v) {
    const isBridge = bridges.some(([a, b]) => (a === u && b === v) || (a === v && b === u));
    if (isBridge) return { stroke: '#ef4444', strokeWidth: 3.5, dash: '', opacity: 1 };

    if (exploringEdge && ((exploringEdge.from === u && exploringEdge.to === v) || (exploringEdge.from === v && exploringEdge.to === u)))
      return { stroke: '#f59e0b', strokeWidth: 3, dash: '8,4', opacity: 1 };

    if (activeEdge && ((activeEdge.from === u && activeEdge.to === v) || (activeEdge.from === v && activeEdge.to === u)))
      return { stroke: '#8b5cf6', strokeWidth: 2.5, dash: '5,3', opacity: 1 };

    return { stroke: '#94a3b8', strokeWidth: 2.2, dash: '', opacity: 0.55 };
  }

  const nodeRadius = 26;
  const allNodes = Object.keys(NODE_POSITIONS);

  return (
    <div className="graph-viz-container">
      <svg
        viewBox="80 15 520 300"
        style={{ width: '100%', height: '100%', minHeight: 260, maxHeight: 380 }}
      >
        <defs>
          <filter id="shadow">
            <feDropShadow dx="1" dy="2" stdDeviation="2" floodOpacity="0.18" />
          </filter>
        </defs>

        {/* Edges */}
        {edges.map(([u, v]) => {
          const pu = NODE_POSITIONS[u];
          const pv = NODE_POSITIONS[v];
          if (!pu || !pv) return null;
          const style = getEdgeStyle(u, v);
          const dx = pv.x - pu.x;
          const dy = pv.y - pu.y;
          const len = Math.sqrt(dx * dx + dy * dy);
          const nx = (dx / len) * nodeRadius;
          const ny = (dy / len) * nodeRadius;
          return (
            <g key={`${u}-${v}`}>
              <line
                x1={pu.x + nx}
                y1={pu.y + ny}
                x2={pv.x - nx}
                y2={pv.y - ny}
                stroke={style.stroke}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.dash || 'none'}
                opacity={style.opacity}
                strokeLinecap="round"
              />
            </g>
          );
        })}

        {/* Nodes */}
        {allNodes.map((node) => {
          const pos = NODE_POSITIONS[node];
          const isArticulation = articulationPoints.includes(node);
          const isCurrent = currentNode === node;
          const isVisited = visitedNodes && visitedNodes.has(node);
          const isHighlight = highlightNodes && highlightNodes.includes(node);
          const hasDfn = dfn && dfn[node] !== undefined;
          const hasLow = low && low[node] !== undefined;

          let fill = '#f1f5f9';
          let stroke = '#94a3b8';
          let strokeW = 2;
          let textColor = '#475569';

          if (isArticulation) {
            fill = '#fecaca';
            stroke = '#ef4444';
            strokeW = 3.5;
            textColor = '#991b1b';
          }
          if (isCurrent) {
            fill = '#bfdbfe';
            stroke = '#3b82f6';
            strokeW = 4;
            textColor = '#1e40af';
          } else if (isVisited && !isArticulation) {
            fill = '#d1fae5';
            stroke = '#10b981';
            strokeW = 2.5;
            textColor = '#065f46';
          }
          if (isHighlight) {
            fill = '#fef08a';
            stroke = '#eab308';
            strokeW = 4;
          }

          return (
            <g
              key={node}
              onMouseEnter={() => setHoveredNode(node)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={nodeRadius}
                fill={fill}
                stroke={stroke}
                strokeWidth={strokeW}
                filter="url(#shadow)"
                style={{ transition: 'all 0.3s ease' }}
              />
              <text
                x={pos.x}
                y={pos.y}
                textAnchor="middle"
                dy="0.35em"
                fill={textColor}
                fontSize="14"
                fontWeight="bold"
                style={{ pointerEvents: 'none', userSelect: 'none' }}
              >
                {node}
              </text>
              {hasDfn && (
                <text
                  x={pos.x + nodeRadius + 4}
                  y={pos.y - 5}
                  fontSize="9"
                  fill="#6366f1"
                  fontWeight="600"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  dfn={dfn[node]}
                </text>
              )}
              {hasLow && (
                <text
                  x={pos.x + nodeRadius + 4}
                  y={pos.y + 7}
                  fontSize="9"
                  fill="#8b5cf6"
                  fontWeight="600"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  low={low[node]}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="legend">
        <div className="legend-item"><span className="legend-dot" style={{ background: '#f1f5f9', border: '2px solid #94a3b8' }}></span> 未访问</div>
        <div className="legend-item"><span className="legend-dot" style={{ background: '#d1fae5', border: '2px solid #10b981' }}></span> 已访问</div>
        <div className="legend-item"><span className="legend-dot" style={{ background: '#bfdbfe', border: '3px solid #3b82f6' }}></span> 当前</div>
        <div className="legend-item"><span className="legend-dot" style={{ background: '#fecaca', border: '3px solid #ef4444' }}></span> 割点</div>
        <div className="legend-item"><span className="legend-line" style={{ background: '#ef4444', height: 3, width: 18 }}></span> 桥</div>
      </div>

      {hoveredNode && (
        <div className="tooltip">
          <strong>{hoveredNode}</strong>
          {dfn && dfn[hoveredNode] !== undefined && <span> dfn={dfn[hoveredNode]}</span>}
          {low && low[hoveredNode] !== undefined && <span> low={low[hoveredNode]}</span>}
        </div>
      )}
    </div>
  );
}