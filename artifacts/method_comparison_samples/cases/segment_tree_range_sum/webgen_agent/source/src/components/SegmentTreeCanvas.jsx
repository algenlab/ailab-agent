import React, { useMemo } from 'react';
import './SegmentTreeCanvas.css';

const NODE_COLORS = {
  root: '#4f46e5',
  inner: '#6366f1',
  leaf: '#8b5cf6',
  'query-hit': '#3b82f6',
  'update-path': '#ef4444',
  highlighted: '#f59e0b',
  default: '#cbd5e1',
  dimmed: '#e2e8f0',
};

function getNodeStyle(nodeId, highlightNodes, treeSnapshot) {
  const isHighlighted = highlightNodes.includes(nodeId);
  const isQueryHit = treeSnapshot?.queryHits?.includes(nodeId);
  const isUpdatePath = treeSnapshot?.updatePath?.includes(nodeId);
  const isQueryVisited = treeSnapshot?.queryVisited?.includes(nodeId);

  if (isUpdatePath) return { borderColor: NODE_COLORS['update-path'], bgColor: '#fef2f2', pulse: true, label: '更新路径' };
  if (isQueryHit) return { borderColor: NODE_COLORS['query-hit'], bgColor: '#eff6ff', pulse: true, label: '命中' };
  if (isHighlighted) return { borderColor: NODE_COLORS.highlighted, bgColor: '#fffbeb', pulse: true, label: '当前关注' };
  if (isQueryVisited) return { borderColor: '#93c5fd', bgColor: '#f8fafc', pulse: false, label: '' };
  return { borderColor: NODE_COLORS.default, bgColor: '#ffffff', pulse: false, label: '' };
}

function TreeNodeComp({ node, highlightNodes, treeSnapshot, depth }) {
  const style = getNodeStyle(node.id, highlightNodes, treeSnapshot);
  const isLeaf = node.isLeaf;

  const nodeClass = [
    'tree-node',
    style.pulse ? 'tree-node--pulse' : '',
    isLeaf ? 'tree-node--leaf' : '',
    !isLeaf ? 'tree-node--inner' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className="tree-node-wrapper" style={{ '--depth': depth }}>
      <div
        className={nodeClass}
        style={{
          borderColor: style.borderColor,
          backgroundColor: style.bgColor,
        }}
      >
        <div className="tree-node__header">
          <span className="tree-node__id">{node.id.replace('seg_', '')}</span>
          {style.label && <span className="tree-node__badge" style={{ background: style.borderColor }}>{style.label}</span>}
        </div>
        <div className="tree-node__range">
          [{node.l}, {node.r}]
        </div>
        <div className="tree-node__sum">
          sum = <strong>{node.sum}</strong>
        </div>
      </div>
      {node.children && node.children.length > 0 && (
        <div className="tree-node__children">
          {node.children.map((child, i) => (
            <TreeNodeComp
              key={child.id}
              node={child}
              highlightNodes={highlightNodes}
              treeSnapshot={treeSnapshot}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SegmentTreeCanvas({ highlightNodes, treeSnapshot, stepIndex, stepTitle }) {
  const treeRoot = useMemo(() => {
    if (!treeSnapshot || !treeSnapshot.nodes) return null;

    const nodeMap = new Map();
    treeSnapshot.nodes.forEach(n => {
      nodeMap.set(n.id, { ...n, children: [] });
    });

    treeSnapshot.nodes.forEach(n => {
      if (!n.isLeaf && n.children) {
        const parent = nodeMap.get(n.id);
        parent.children = n.children.map(c => nodeMap.get(c.id)).filter(Boolean);
      }
    });

    return nodeMap.get('seg_0_3') || null;
  }, [treeSnapshot]);

  return (
    <div className="segment-tree-canvas">
      <div className="canvas-info">
        <span className="step-indicator">步骤 {stepIndex + 1}</span>
        <span className="step-title-text">{stepTitle || '线段树'}</span>
      </div>
      {treeRoot ? (
        <div className="tree-container">
          <TreeNodeComp
            node={treeRoot}
            highlightNodes={highlightNodes}
            treeSnapshot={treeSnapshot}
            depth={0}
          />
        </div>
      ) : (
        <div className="tree-empty">请通过步骤导航器查看线段树状态。</div>
      )}
      <div className="canvas-legend">
        <span className="legend-item"><span className="legend-dot" style={{ background: '#f59e0b' }}></span> 当前关注</span>
        <span className="legend-item"><span className="legend-dot" style={{ background: '#3b82f6' }}></span> 查询命中</span>
        <span className="legend-item"><span className="legend-dot" style={{ background: '#ef4444' }}></span> 更新路径</span>
        <span className="legend-item"><span className="legend-dot" style={{ background: '#cbd5e1' }}></span> 普通节点</span>
      </div>
    </div>
  );
}
