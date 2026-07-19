import React from 'react';
import { SegmentTreeNode } from '../types';

interface Props {
  nodesByLevel: SegmentTreeNode[][];
  highlightedPath: number[];
  visitedNodes: number[];
  nums: number[];
}

const treeContainerStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-md)',
  padding: '24px 16px',
  marginBottom: '16px',
  boxShadow: 'var(--shadow)',
  overflowX: 'auto',
  minHeight: '220px',
};

const levelRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'center',
  gap: '12px',
  marginBottom: '16px',
  flexWrap: 'nowrap',
};

const levelLabelStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  textAlign: 'center',
  marginBottom: '6px',
};

const placeholderStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '48px 16px',
  color: '#64748b',
};

const stepHintStyle: React.CSSProperties = {
  display: 'flex',
  gap: '16px',
  justifyContent: 'center',
  flexWrap: 'wrap',
  marginTop: '16px',
};

const stepBubble: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '20px',
  background: '#1e3a5f',
  border: '1px solid #334155',
  fontSize: '0.8rem',
  color: '#94a3b8',
};

function getNodeStyle(
  node: SegmentTreeNode,
  highlightedPath: number[],
  visitedNodes: number[],
  _nums: number[]
): React.CSSProperties {
  const isHighlighted = highlightedPath.includes(node.id);
  const isVisited = visitedNodes.includes(node.id);
  const isLeaf = node.l === node.r;

  let bg = '#1e3a5f';
  let border = '#3b82f6';
  let glow = 'none';

  if (isLeaf) {
    bg = '#065f46';
    border = '#10b981';
  }

  if (isHighlighted) {
    bg = '#5b21b6';
    border = '#a78bfa';
    glow = '0 0 12px rgba(167, 139, 250, 0.5)';
  } else if (isVisited && !isHighlighted) {
    bg = '#1e3a5f';
    border = '#60a5fa';
    glow = '0 0 6px rgba(96, 165, 250, 0.3)';
  }

  return {
    background: bg,
    border: `2px solid ${border}`,
    borderRadius: 'var(--radius-sm)',
    padding: '12px 16px',
    minWidth: '110px',
    textAlign: 'center' as const,
    boxShadow: glow,
    transition: 'all 0.3s ease',
    color: '#f1f5f9',
  };
}

export default function SegmentTreeView({
  nodesByLevel,
  highlightedPath,
  visitedNodes,
  nums,
}: Props) {
  return (
    <div style={treeContainerStyle}>
      <h3
        style={{
          fontSize: '1rem',
          fontWeight: 700,
          color: '#e2e8f0',
          marginBottom: '12px',
        }}
      >
        🌳 Segment Tree Visualization
      </h3>

      {nodesByLevel.length === 0 ? (
        <div style={placeholderStyle}>
          <div style={{ fontSize: '3rem', marginBottom: '12px', opacity: 0.5 }}>
            🌲
          </div>
          <p style={{ fontSize: '0.95rem', color: '#94a3b8', marginBottom: '8px' }}>
            The segment tree will appear here once built.
          </p>
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Click <strong style={{ color: '#60a5fa' }}>🔨 Build Tree</strong> to
            construct the tree from the input array <strong>[2, 1, 4, 5]</strong>.
          </p>
          <div style={stepHintStyle}>
            <div style={stepBubble}>1. Build Tree</div>
            <div style={stepBubble}>2. Query Range</div>
            <div style={stepBubble}>3. Apply Update</div>
            <div style={stepBubble}>4. Re-query</div>
          </div>
        </div>
      ) : (
        <>
          <div
            style={{
              fontSize: '0.8rem',
              color: '#94a3b8',
              marginBottom: '16px',
              display: 'flex',
              gap: '20px',
              flexWrap: 'wrap',
            }}
          >
            <span>🟣 Highlighted = active path</span>
            <span>🔵 Visited = query traversal</span>
            <span>🟢 Green border = leaf node</span>
          </div>
          {nodesByLevel.map((level, levelIdx) => (
            <div key={levelIdx}>
              <div style={levelLabelStyle}>Level {levelIdx}</div>
              <div style={levelRowStyle}>
                {level.map((node) => (
                  <div
                    key={node.id}
                    style={getNodeStyle(node, highlightedPath, visitedNodes, nums)}
                    title={`Node id=${node.id}, range=[${node.l},${node.r}], sum=${node.sum}`}
                  >
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      [{node.l}, {node.r}]
                    </div>
                    <div
                      style={{
                        fontSize: '1.4rem',
                        fontWeight: 700,
                        color: '#38bdf8',
                      }}
                    >
                      {node.sum}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: '#64748b' }}>
                      id:{node.id}
                    </div>
                  </div>
                ))}
              </div>
              {levelIdx < nodesByLevel.length - 1 && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    marginBottom: '8px',
                  }}
                >
                  {level.map((node) => {
                    const hasChildren =
                      node.left !== null || node.right !== null;
                    if (!hasChildren) return null;
                    return (
                      <div
                        key={`edge-${node.id}`}
                        style={{
                          width: '110px',
                          margin: '0 6px',
                          display: 'flex',
                          justifyContent: 'center',
                        }}
                      >
                        <svg
                          width="110"
                          height="20"
                          style={{ display: 'block' }}
                        >
                          <line
                            x1="55"
                            y1="0"
                            x2="20"
                            y2="18"
                            stroke="#475569"
                            strokeWidth="1.5"
                          />
                          <line
                            x1="55"
                            y1="0"
                            x2="90"
                            y2="18"
                            stroke="#475569"
                            strokeWidth="1.5"
                          />
                        </svg>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
