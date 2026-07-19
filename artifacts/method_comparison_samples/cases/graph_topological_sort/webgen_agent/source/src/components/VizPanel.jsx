import React from 'react';

export function VizPanel({ state, stepIndex, totalSteps, isDone, onPrev, onNext, onReset }) {
  const { indegree, queue, result, currentNode, changedNodes } = state;

  const isStart = stepIndex === 0;
  const isEnd = stepIndex >= totalSteps - 1;
  const progressPct = totalSteps > 1 ? Math.round((stepIndex / (totalSteps - 1)) * 100) : 0;

  return (
    <div className="card full-width">
      <h2>🔍 逐步可视化</h2>
      <div className="viz-panel">
        {/* Indegree Table */}
        <div className="state-box">
          <div className="state-label">入度表 (indegree)</div>
          <div className="indegree-grid">
            {Object.entries(indegree).map(([node, deg]) => (
              <div
                key={node}
                className={`indegree-cell ${deg === 0 ? 'zero' : 'positive'} ${changedNodes?.includes(node) ? 'changed' : ''}`}
              >
                {node}: {deg}
              </div>
            ))}
          </div>
        </div>

        {/* Queue */}
        <div className="state-box">
          <div className="state-label">队列 (queue)</div>
          <div className="queue-items">
            {queue.length === 0
              ? <span className="empty-inline">— 空 —</span>
              : queue.map((n, i) => (
                  <span key={i} className={`queue-item ${i === 0 && currentNode === n ? '' : ''}`}>
                    {n}
                    {i === 0 && <span style={{ fontSize: '0.7rem', marginLeft: 4 }}>←头部</span>}
                  </span>
                ))
            }
          </div>
        </div>

        {/* Result */}
        <div className="state-box">
          <div className="state-label">已处理结果 (result)</div>
          <div className="state-value">
            {result.length > 0
              ? `[${result.join(', ')}]`
              : <span className="empty-inline">暂无结果 — 点击"下一步"开始</span>
            }
          </div>
        </div>

        {/* Current Node */}
        {currentNode && (
          <div className="state-box" style={{ background: 'var(--warning-light)', borderColor: 'var(--warning)' }}>
            <div className="state-label">当前弹出节点</div>
            <div className="state-value" style={{ color: 'var(--warning)', fontSize: '1.2rem' }}>
              {currentNode}
            </div>
          </div>
        )}

        {isDone && (
          <div className="state-box" style={{ background: 'var(--success-light)', borderColor: 'var(--success)' }}>
            <div className="state-label">✅ 算法完成</div>
            <div className="state-value" style={{ color: 'var(--success)' }}>
              最终结果: [{result.join(', ')}]
            </div>
          </div>
        )}

        {/* Navigation with progress bar */}
        <div className="nav-section">
          <div className="nav-controls">
            <button className="btn btn-outline btn-sm" onClick={onReset} disabled={isStart}>
              ⏮ 重置
            </button>
            <button className="btn btn-outline" onClick={onPrev} disabled={isStart}>
              ◀ 上一步
            </button>
            <span className="step-indicator">
              步骤 {stepIndex} / {totalSteps - 1}
            </span>
            <button className="btn btn-primary" onClick={onNext} disabled={isEnd}>
              下一步 ▶
            </button>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
