import React, { useState, useMemo } from 'react';
import './UnionFindVisualizer.css';

function countRoots(parent) {
  const roots = new Set();
  for (let i = 0; i < parent.length; i++) {
    let x = i;
    while (parent[x] !== x) {
      x = parent[x];
    }
    roots.add(x);
  }
  return roots.size;
}

function findFullRoot(parent, x) {
  while (parent[x] !== x) {
    x = parent[x];
  }
  return x;
}

export default function UnionFindVisualizer({ ufState, input }) {
  const { snapshot, currentStep, totalSteps, goToStep, stepForward, stepBackward, reset, goToEnd } = ufState;

  if (!snapshot) {
    return (
      <div className="card visualizer-card">
        <div className="card-header">🔍 算法可视化</div>
        <p className="loading-text">正在加载...</p>
      </div>
    );
  }

  const { parent, rank, componentCount, action, step } = snapshot;
  const n = parent.length;
  const rootCount = countRoots(parent);

  const progressPercent = totalSteps > 1 ? ((currentStep + 1) / totalSteps) * 100 : 100;

  return (
    <div className="card visualizer-card">
      <div className="card-header">
        <span>🔍</span> 并查集算法逐步追踪
        <span className="step-badge">步骤 {step + 1} / {totalSteps}</span>
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progressPercent}%` }} />
      </div>

      <div className="action-display">
        <span className="action-label">当前操作：</span>
        <span className="action-text">{action}</span>
      </div>

      <div className="state-panels">
        <div className="state-panel">
          <h5>parent 数组</h5>
          <div className="array-grid">
            {parent.map((val, idx) => {
              const isRoot = val === idx;
              const fullRoot = findFullRoot(parent, idx);
              return (
                <div
                  key={idx}
                  className={`array-cell ${isRoot ? 'cell-root' : 'cell-child'}`}
                  title={`parent[${idx}] = ${val}，根节点 = ${fullRoot}`}
                >
                  <span className="cell-index">{idx}</span>
                  <span className="cell-value">{val}</span>
                  {isRoot && <span className="cell-root-badge">根</span>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="state-panel">
          <h5>rank 数组</h5>
          <div className="array-grid">
            {rank.map((val, idx) => (
              <div key={idx} className="array-cell cell-rank" title={`rank[${idx}] = ${val}`}>
                <span className="cell-index">{idx}</span>
                <span className="cell-value">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="province-summary">
        <div className="summary-item">
          <span className="summary-label">当前省份数量：</span>
          <span className="summary-value highlight">{rootCount}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">合并操作次数：</span>
          <span className="summary-value">{n - rootCount}</span>
        </div>
      </div>

      <div className="connectivity-graph">
        <h5>连通关系图</h5>
        <div className="graph-container">
          {Array.from({ length: n }, (_, i) => {
            const root = findFullRoot(parent, i);
            return (
              <div key={i} className="graph-node-group">
                <div className={`graph-node ${parent[i] === i ? 'node-root' : 'node-leaf'}`}>
                  <span className="node-id">{i}</span>
                </div>
                {parent[i] !== i && (
                  <div className="node-arrow">
                    <span>→</span>
                    <span className="arrow-target">{parent[i]}</span>
                  </div>
                )}
                <div className="node-province-badge" style={{ background: getProvinceColor(root, n) }}>
                  省份 {root}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="nav-controls">
        <button onClick={reset} disabled={currentStep === 0} className="nav-btn nav-btn-reset">
          ⏮ 重置
        </button>
        <button onClick={stepBackward} disabled={currentStep === 0} className="nav-btn">
          ◀ 上一步
        </button>
        <input
          type="range"
          min={0}
          max={totalSteps - 1}
          value={currentStep}
          onChange={(e) => goToStep(parseInt(e.target.value))}
          className="step-slider"
        />
        <button onClick={stepForward} disabled={currentStep >= totalSteps - 1} className="nav-btn">
          下一步 ▶
        </button>
        <button onClick={goToEnd} disabled={currentStep >= totalSteps - 1} className="nav-btn nav-btn-end">
          ⏭ 最终
        </button>
      </div>
    </div>
  );
}

function getProvinceColor(root, n) {
  const colors = ['#4f46e5', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#be123c', '#4d7c0f'];
  return colors[root % colors.length];
}