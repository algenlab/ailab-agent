import React from 'react';

function TreeNodeView({ node, highlightNode, processedNodes }) {
  const isHighlight = node.id === highlightNode;
  const isProcessed = processedNodes.includes(node.id);
  let circleClass = 'node-circle';
  if (isHighlight) circleClass += ' highlight';
  else if (isProcessed) circleClass += ' processed';

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="tree-node">
      <div className={circleClass} title={`Node ${node.id} (value: ${node.value})`}>
        <span className="node-id">{node.id}</span>
        <span className="node-value">v:{node.value}</span>
      </div>
      {hasChildren && (
        <div className="tree-children">
          {node.children.map(child => (
            <div className="tree-child-wrapper" key={child.id}>
              <TreeNodeView node={child} highlightNode={highlightNode} processedNodes={processedNodes} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TreeVisualization({ tree, highlightNode, processedNodes = [] }) {
  if (!tree) {
    return <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }}>Tree data unavailable.</div>;
  }
  return (
    <div className="tree-container">
      <TreeNodeView node={tree} highlightNode={highlightNode} processedNodes={processedNodes} />
    </div>
  );
}