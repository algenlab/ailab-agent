import React from 'react';

function TreeView({ heap }){
  if (!heap || heap.length === 0) return <div className="empty-heap">Empty heap</div>;
  // Build a list of nodes with positions for a binary tree layout
  const nodes = heap.map((value, idx) => {
    return { value, index: idx };
  });
  const depth = Math.floor(Math.log2(heap.length)) + 1;
  const maxNodes = Math.pow(2, depth) - 1;
  // Create a grid layout: each row centered
  const rows = [];
  let nodeIdx = 0;
  for (let d = 0; d < depth; d++) {
    const levelCount = Math.pow(2, d);
    const row = [];
    for (let i = 0; i < levelCount; i++) {
      if (nodeIdx < heap.length) {
        row.push(heap[nodeIdx]);
      } else {
        row.push(null);
      }
      nodeIdx++;
    }
    rows.push(row);
  }

  return (
    <div className="tree-container">
      {rows.map((row, rowIdx) => (
        <div key={rowIdx} className="tree-row" style={{ '--level-items': row.length }}>
          {row.map((val, colIdx) => (
            <div key={colIdx} className={`tree-node ${val === null ? 'hidden' : ''}`}>
              {val !== null && <span className="node-value">{val}</span>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function HeapVisualizer({ heapBefore, heapAfter, topBefore, topAfter, action, reason }) {
  return (
    <div className="heap-visualizer card">
      <h2>Heap State</h2>
      <div className="heap-panels">
        <div className="heap-panel">
          <h3>Before</h3>
          <TreeView heap={heapBefore} />
          <div className="heap-info">Top: <code>{topBefore !== null ? topBefore : '—'}</code></div>
        </div>
        <div className="heap-panel">
          <h3>After</h3>
          <TreeView heap={heapAfter} />
          <div className="heap-info">Top: <code>{topAfter !== null ? topAfter : '—'}</code></div>
        </div>
      </div>
      <div className="action-reason">
        <span className="action-badge">{action}</span>
        <p className="reason-text">{reason}</p>
      </div>
    </div>
  );
}
  