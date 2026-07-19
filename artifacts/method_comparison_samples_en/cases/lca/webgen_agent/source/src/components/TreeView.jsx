import React from 'react';
import { EDGE_LIST, TREE_NODE_MAP, P_TARGET, Q_TARGET } from '../data';

/**
 * TreeView — renders the binary tree as an SVG diagram.
 *
 * Props:
 *   highlightNodes  : array of node IDs to highlight (current step)
 *   currentNode     : the node currently being processed (or null)
 *   lcaFound        : boolean — whether the LCA has been identified
 *   targetNodes     : [p, q] — the two target node IDs
 */
export default function TreeView({ highlightNodes = [], currentNode = null, lcaFound = false, targetNodes = [P_TARGET, Q_TARGET] }) {
  const highlightSet = new Set(highlightNodes);
  const targetSet = new Set(targetNodes);

  function getNodeClass(nodeId) {
    const isCurrent = nodeId === currentNode;
    const isTarget = targetSet.has(nodeId);
    const isHighlighted = highlightSet.has(nodeId);
    const isLca = lcaFound && nodeId === '3'; // LCA is always 3 in this problem

    if (isLca) return 'lca';
    if (isCurrent && isTarget) return 'current-target';
    if (isCurrent) return 'current';
    if (isTarget && isHighlighted) return 'target';
    if (isTarget) return 'target';
    return 'default';
  }

  function getEdgeClass(from, to) {
    if (highlightSet.has(from) && highlightSet.has(to)) return 'tree-edge highlight';
    return 'tree-edge';
  }

  const nodeRadius = 24;

  return (
    <div className="tree-view-container" aria-label="Binary tree visualization">
      <svg viewBox="0 0 800 430" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Binary tree diagram showing 9 nodes">
        {/* Edge lines */}
        {EDGE_LIST.map((edge) => (
          <line
            key={`${edge.from}-${edge.to}`}
            x1={edge.x1}
            y1={edge.y1 + nodeRadius}
            x2={edge.x2}
            y2={edge.y2 - nodeRadius}
            className={getEdgeClass(edge.from, edge.to)}
          />
        ))}

        {/* Node circles */}
        {Object.values(TREE_NODE_MAP).map((node) => {
          const nodeClass = getNodeClass(node.id);
          const isOnHighlight = nodeClass === 'current' || nodeClass === 'lca' || nodeClass === 'current-target';
          return (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r={nodeRadius}
                className={`tree-node-circle ${nodeClass}`}
              />
              <text
                x={node.x}
                y={node.y}
                className={`tree-node-text${isOnHighlight ? ' on-highlight' : ''}`}
              >
                {node.id}
              </text>
            </g>
          );
        })}

        {/* p, q labels next to target nodes */}
        {targetNodes.map((tid, idx) => {
          const node = TREE_NODE_MAP[tid];
          if (!node) return null;
          const label = idx === 0 ? 'p' : 'q';
          const offsetX = idx === 0 ? -38 : 38;
          return (
            <text
              key={`label-${tid}`}
              x={node.x + offsetX}
              y={node.y - 28}
              className="tree-node-text"
              style={{ fontSize: '11px', fontWeight: 600, fill: '#d97706' }}
            >
              {label} = "{tid}"
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="tree-legend" aria-label="Color legend for tree nodes">
        <span className="legend-item">
          <span className="legend-dot default"></span> Default node
        </span>
        <span className="legend-item">
          <span className="legend-dot target"></span> Target (p / q)
        </span>
        <span className="legend-item">
          <span className="legend-dot current"></span> Current node
        </span>
        <span className="legend-item">
          <span className="legend-dot lca"></span> LCA found
        </span>
      </div>
    </div>
  );
}
