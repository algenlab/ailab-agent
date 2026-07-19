import React from 'react';

// Simple SVG graph visualization for the directed weighted graph
export default function GraphViz({ graph, start, highlightNode, highlightEdge }) {
  // Layout positions for nodes A, B, C in a triangle
  const positions = {
    A: { x: 80, y: 180 },
    B: { x: 240, y: 60 },
    C: { x: 240, y: 300 }
  };

  const nodeRadius = 32;

  // Collect all unique edges with weights
  const edges = [];
  Object.entries(graph).forEach(([from, neighbors]) => {
    neighbors.forEach(([to, weight]) => {
      edges.push({ from, to, weight });
    });
  });

  // Helper to compute edge path with offset for parallel edges
  const getEdgePath = (from, to) => {
    const f = positions[from];
    const t = positions[to];
    if (!f || !t) return '';

    const dx = t.x - f.x;
    const dy = t.y - f.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ux = dx / len;
    const uy = dy / len;

    // Start from the edge of the circle
    const startX = f.x + ux * nodeRadius;
    const startY = f.y + uy * nodeRadius;

    // End before the target circle (leave room for arrowhead)
    const endX = t.x - ux * (nodeRadius + 6);
    const endY = t.y - uy * (nodeRadius + 6);

    // Midpoint for curved edges
    const midX = (startX + endX) / 2;
    const midY = (startY + endY) / 2;

    // Perpendicular offset for curve
    const perpX = -uy * 22;
    const perpY = ux * 22;

    const cx = midX + perpX;
    const cy = midY + perpY;

    return `M${startX},${startY} Q${cx},${cy} ${endX},${endY}`;
  };

  const isHighlighted = (from, to) => {
    if (!highlightEdge) return false;
    return highlightEdge.from === from && highlightEdge.to === to;
  };

  const isNodeHighlighted = (node) => {
    if (!highlightNode) return false;
    return highlightNode === node;
  };

  const isStartNode = (node) => node === start;

  return (
    <svg
      viewBox="0 0 360 380"
      style={{
        width: '100%',
        maxWidth: '360px',
        height: 'auto',
        display: 'block',
        margin: '0 auto'
      }}
      aria-label="Directed graph visualization showing nodes A, B, C with weighted edges"
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="10"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#636e72" />
        </marker>
        <marker
          id="arrowhead-highlight"
          markerWidth="10"
          markerHeight="7"
          refX="10"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#e17055" />
        </marker>
        {/* Drop shadow filter */}
        <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#00000022" />
        </filter>
      </defs>

      {/* Background subtle grid for visual appeal */}
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e8ecf1" strokeWidth="0.5" />
      </pattern>
      <rect x="0" y="0" width="360" height="380" fill="url(#grid)" rx="8" />

      {/* Edges */}
      {edges.map((e, i) => {
        const highlighted = isHighlighted(e.from, e.to);
        return (
          <g key={i}>
            {/* Invisible wider path for easier click/hit area */}
            <path
              d={getEdgePath(e.from, e.to)}
              fill="none"
              stroke="transparent"
              strokeWidth="14"
            />
            <path
              d={getEdgePath(e.from, e.to)}
              fill="none"
              stroke={highlighted ? '#e17055' : '#636e72'}
              strokeWidth={highlighted ? 3 : 2.2}
              markerEnd={highlighted ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'}
              style={{ transition: 'stroke 0.3s, stroke-width 0.3s' }}
            />
            {/* Weight label background for readability */}
            <text fontSize="15" fontWeight="700" fill={highlighted ? '#e17055' : '#2d3436'}>
              <textPath href={`#edge-label-${i}`} startOffset="50%" textAnchor="middle">
                {e.weight}
              </textPath>
            </text>
            {/* Hidden path for text positioning */}
            <path
              id={`edge-label-${i}`}
              d={getEdgePath(e.from, e.to)}
              fill="none"
              stroke="none"
            />
          </g>
        );
      })}

      {/* Nodes */}
      {Object.keys(positions).map((node) => {
        const pos = positions[node];
        const highlighted = isNodeHighlighted(node);
        const isStart = isStartNode(node);
        return (
          <g key={node} filter="url(#nodeShadow)">
            <circle
              cx={pos.x}
              cy={pos.y}
              r={nodeRadius}
              fill={highlighted ? '#e17055' : isStart ? '#0f3460' : '#ffffff'}
              stroke={highlighted ? '#d63031' : isStart ? '#0a2647' : '#b2bec3'}
              strokeWidth={highlighted ? 3.5 : 2.5}
              style={{ transition: 'fill 0.3s, stroke 0.3s' }}
            />
            <text
              x={pos.x}
              y={pos.y + 1}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize="18"
              fontWeight="700"
              fill={isStart || highlighted ? '#ffffff' : '#2d3436'}
              style={{ pointerEvents: 'none' }}
            >
              {node}
            </text>
            {isStart && (
              <text
                x={pos.x}
                y={pos.y - nodeRadius - 14}
                textAnchor="middle"
                fontSize="11"
                fontWeight="700"
                fill="#0f3460"
              >
                START
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
