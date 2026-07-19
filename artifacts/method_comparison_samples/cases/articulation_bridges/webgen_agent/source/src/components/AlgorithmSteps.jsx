import React, { useState, useEffect, useRef } from 'react';

export default function AlgorithmSteps({ steps, currentStep, onStepChange, graph }) {
  const logRef = useRef(null);
  const allNodes = Object.keys(graph).sort();
  const [logExpanded, setLogExpanded] = useState(false);

  useEffect(() => {
    if (logRef.current && logExpanded) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [currentStep, logExpanded]);

  const step = steps[currentStep];
  if (!step) return null;

  const hasParentData = step.parent && Object.keys(step.parent).length > 0;

  return (
    <div className="algo-steps-panel">
      <div className="algo-header">
        <h3>🔍 算法步骤追踪</h3>
        <div className="step-counter">
          步骤 {currentStep + 1} / {steps.length}
        </div>
      </div>

      <div className="step-nav">
        <button
          onClick={() => onStepChange(0)}
          disabled={currentStep === 0}
          className="nav-btn"
          title="第一步"
        >
          ⏮
        </button>
        <button
          onClick={() => onStepChange(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
          className="nav-btn"
        >
          ◀ 上一步
        </button>
        <button
          onClick={() => onStepChange(Math.min(steps.length - 1, currentStep + 1))}
          disabled={currentStep === steps.length - 1}
          className="nav-btn"
        >
          下一步 ▶
        </button>
        <button
          onClick={() => onStepChange(steps.length - 1)}
          disabled={currentStep === steps.length - 1}
          className="nav-btn"
          title="最后一步"
        >
          ⏭
        </button>
      </div>

      <div className="current-step-info">
        <span className={`step-badge step-${step.type}`}>
          {getStepLabel(step.type)}
        </span>
        <p className="step-description">{step.description}</p>
      </div>

      <div className="state-tables">
        <div className="state-table">
          <h4>dfn 数组</h4>
          <table>
            <thead>
              <tr>
                {allNodes.map(k => <th key={k}>{k}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                {allNodes.map(k => (
                  <td
                    key={k}
                    className={
                      step.node === k ? 'highlight-cell' :
                      step.dfn[k] === undefined ? 'unset-cell' : ''
                    }
                  >
                    {step.dfn[k] !== undefined ? step.dfn[k] : '–'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        <div className="state-table">
          <h4>low 数组</h4>
          <table>
            <thead>
              <tr>
                {allNodes.map(k => <th key={k}>{k}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                {allNodes.map(k => (
                  <td
                    key={k}
                    className={
                      step.node === k ? 'highlight-cell' :
                      step.low[k] === undefined ? 'unset-cell' : ''
                    }
                  >
                    {step.low[k] !== undefined ? step.low[k] : '–'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {hasParentData && (
        <div className="state-table" style={{ marginBottom: 6 }}>
          <h4>parent 数组</h4>
          <table>
            <thead>
              <tr>
                {Object.keys(step.parent).sort().map(k => <th key={k}>{k}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                {Object.keys(step.parent).sort().map(k => (
                  <td key={k}>{step.parent[k] !== undefined ? step.parent[k] : '–'}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <div className="log-toggle-bar">
        <button
          className="log-toggle-btn"
          onClick={() => setLogExpanded(!logExpanded)}
        >
          {logExpanded ? '▼' : '▶'} 执行日志
          <span className="log-count-badge">{currentStep + 1}/{steps.length}</span>
        </button>
      </div>

      {logExpanded && (
        <div className="step-log" ref={logRef}>
          {steps.slice(0, currentStep + 1).map((s, i) => (
            <div
              key={i}
              className={`log-entry ${i === currentStep ? 'log-current' : ''} log-${s.type}`}
              onClick={() => onStepChange(i)}
            >
              <span className="log-num">#{s.stepNum}</span>
              <span className="log-text">{s.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function getStepLabel(type) {
  const map = {
    'start-component': '🚩 新分量',
    'enter': '⬇ 进入节点',
    'explore': '🔎 探索邻居',
    'backtrack': '⬆ 回溯',
    'back-edge': '↩ 回边',
    'articulation-found': '🔴 发现割点',
    'bridge-found': '🔗 发现桥',
    'root-articulation': '🔴 根割点',
    'exit': '⬆ 离开节点',
    'complete': '✅ 完成'
  };
  return map[type] || type;
}