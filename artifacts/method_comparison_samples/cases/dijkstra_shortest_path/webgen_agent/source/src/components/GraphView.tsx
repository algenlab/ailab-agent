import React from 'react';
import { AlgorithmStep, NodePosition, RelaxedEdge } from '../types';
import { nodePositions } from '../data';

interface Props {
  step: AlgorithmStep;
  stepIndex: number;
  relaxedEdges: RelaxedEdge[];
  hoveredEdge: string | null;
  onEdgeHover: (key: string | null) => void;
}

const NODE_RADIUS = 26;

function getEdgeEndpoints(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  r: number
) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return { sx: x1, sy: y1, ex: x2, ey: y2, mx: x1, my: y1 };
  const ox = (dx / len) * r;
  const oy = (dy / len) * r;
  return {
    sx: x1 + ox,
    sy: y1 + oy,
    ex: x2 - ox,
    ey: y2 - oy,
    mx: (x1 + x2) / 2,
    my: (y1 + y2) / 2,
  };
}

function getEdgeKey(from: string, to: string) {
  return `${from}->${to}`;
}

const GraphView: React.FC<Props> = ({ step, stepIndex, relaxedEdges, hoveredEdge, onEdgeHover }) => {
  const knownEdges: [string, string, number][] = [
    ['A', 'B', 2],
    ['A', 'C', 5],
    ['B', 'C', 1],
  ];

  const allEdges: { from: string; to: string; weight: number }[] = [];
  const addedEdges = new Set<string>();

  for (const [from, to, weight] of knownEdges) {
    const key = getEdgeKey(from, to);
    if (!addedEdges.has(key)) {
      addedEdges.add(key);
      allEdges.push({ from, to, weight });
    }
  }

  const relaxedEdgeKeys = new Set(
    relaxedEdges.map((re) => getEdgeKey(re.from, re.to))
  );

  const allNodes = Object.keys(nodePositions);

  return (
    <div className="graph-container">
      <svg
        className="graph-svg"
        viewBox="0 0 500 400"
        xmlns="http://www.w3.org/2000/svg"
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
            <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
          </marker>
          <marker
            id="arrowhead-updated"
            markerWidth="10"
            markerHeight="7"
            refX="10"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#16a34a" />
          </marker>
          <marker
            id="arrowhead-highlight"
            markerWidth="10"
            markerHeight="7"
            refX="10"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
          </marker>
        </defs>

        {/* Edges */}
        {allEdges.map(({ from, to, weight }) => {
          const fp = nodePositions[from];
          const tp = nodePositions[to];
          if (!fp || !tp) return null;
          const { sx, sy, ex, ey, mx, my } = getEdgeEndpoints(
            fp.x,
            fp.y,
            tp.x,
            tp.y,
            NODE_RADIUS
          );
          const key = getEdgeKey(from, to);
          const matchingRelaxed = relaxedEdges.find(
            (re) => getEdgeKey(re.from, re.to) === key
          );
          const isRelaxedUpdated = matchingRelaxed?.updated === true;
          const isRelaxedUnchanged = matchingRelaxed?.updated === false;
          const isHovered = hoveredEdge === key;

          let edgeClass = 'edge-line';
          let markerEnd = 'url(#arrowhead)';
          if (isRelaxedUpdated) {
            edgeClass += ' relaxed-updated';
            markerEnd = 'url(#arrowhead-updated)';
          } else if (isRelaxedUnchanged) {
            edgeClass += ' relaxed-unchanged';
          }
          if (isHovered) {
            edgeClass += ' highlight';
            markerEnd = 'url(#arrowhead-highlight)';
          }

          const dx = ex - sx;
          const dy = ey - sy;
          const len = Math.sqrt(dx * dx + dy * dy);
          const perpX = len > 0 ? (-dy / len) * 16 : 0;
          const perpY = len > 0 ? (dx / len) * 16 : 0;

          return (
            <g key={key}>
              <line
                x1={sx}
                y1={sy}
                x2={ex}
                y2={ey}
                className={edgeClass}
                markerEnd={markerEnd}
                onMouseEnter={() => onEdgeHover(key)}
                onMouseLeave={() => onEdgeHover(null)}
                style={{ cursor: 'pointer' }}
              />
              <text
                x={mx + perpX}
                y={my + perpY}
                className="edge-weight"
                textAnchor="middle"
                dominantBaseline="middle"
                onMouseEnter={() => onEdgeHover(key)}
                onMouseLeave={() => onEdgeHover(null)}
                style={{ cursor: 'pointer' }}
              >
                {weight}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {allNodes.map((node) => {
          const pos = nodePositions[node];
          if (!pos) return null;
          const isVisited = step.visited.includes(node);
          const isCurrent = step.poppedNode === node && !step.isFinal;
          const isStart = node === 'A';

          let nodeClass = 'node-circle default';
          if (isCurrent) {
            nodeClass = 'node-circle current';
          } else if (isVisited) {
            nodeClass = 'node-circle visited';
          }
          if (isStart && stepIndex === 0) {
            nodeClass += ' start';
          }

          const dist = step.distances[node];
          const distStr =
            dist === undefined || dist === Infinity
              ? '∞'
              : typeof dist === 'string'
              ? dist
              : String(dist);

          return (
            <g key={node} style={{ cursor: 'pointer' }}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_RADIUS}
                className={nodeClass}
              />
              <text
                x={pos.x}
                y={pos.y + 4}
                className="node-label"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {node}
              </text>
              <text
                x={pos.x}
                y={pos.y + NODE_RADIUS + 18}
                className="distance-label"
                textAnchor="middle"
              >
                {distStr}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default GraphView;
