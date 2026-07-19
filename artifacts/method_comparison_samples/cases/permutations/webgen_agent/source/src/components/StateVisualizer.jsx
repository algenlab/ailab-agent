import React, { useRef, useEffect } from 'react';

export default function StateVisualizer({ step, nums, isNewResult }) {
  const resultEndRef = useRef(null);

  useEffect(() => {
    if (isNewResult && resultEndRef.current) {
      resultEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [step?.id, isNewResult]);

  if (!step) {
    return (
      <div className="card area-viz">
        <div className="card-header">
          <div className="icon icon-green">🔬</div>
          <h2>算法状态可视化</h2>
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>等待开始...</p>
      </div>
    );
  }

  const actionClassMap = {
    init: 'action-init',
    try: 'action-try',
    select: 'action-select',
    complete: 'action-complete',
    backtrack: 'action-backtrack',
    done: 'action-done',
  };

  const actionBarClass = actionClassMap[step.action] || 'action-init';

  // Determine the state of each number in nums
  function getNumState(index) {
    if (step.candidateIndex === index && step.action === 'try') return 'considering';
    if (step.candidateIndex === index && step.action === 'select') return 'selected';
    if (step.used[index]) return 'used';
    return 'available';
  }

  const numStateClassMap = {
    available: 'num-available',
    used: 'num-used',
    considering: 'num-considering',
    selected: 'num-selected',
  };

  const isCompleteAction = step.action === 'complete';
  const prevResultLen = step.id > 0 ? 0 : 0;

  return (
    <div className="card area-viz">
      <div className="card-header">
        <div className="icon icon-green">🔬</div>
        <h2>算法状态可视化</h2>
      </div>
      <div className="state-viz">
        {/* Action description bar */}
        <div className={`state-action-bar ${actionBarClass}`}>
          {step.description}
        </div>

        {/* Nums display */}
        <div className="state-section">
          <span className="state-section-label">📊 数字数组 nums</span>
          <div className="nums-row">
            {nums.map((n, i) => {
              const state = getNumState(i);
              return (
                <div key={i} className={`num-cell ${numStateClassMap[state]}`}>
                  <span className="num-index">{i}</span>
                  {n}
                </div>
              );
            })}
          </div>
        </div>

        {/* Path display */}
        <div className="state-section">
          <span className="state-section-label">🛤 当前路径 path</span>
          <div className="path-row">
            {step.path.length === 0 ? (
              <span className="path-empty">空路径 []</span>
            ) : (
              step.path.map((val, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <span className="path-arrow">→</span>}
                  <span className={`path-box${i === step.path.length - 1 && step.action === 'select' ? ' newest' : ''}`}>
                    {val}
                  </span>
                </React.Fragment>
              ))
            )}
            <span className="path-depth">深度 {step.depth}</span>
          </div>
        </div>

        {/* Used array display */}
        <div className="state-section">
          <span className="state-section-label">🏷 used 数组</span>
          <div className="used-row">
            {step.used.map((u, i) => (
              <div
                key={i}
                className={`used-cell ${u ? 'used-true' : 'used-false'}${step.candidateIndex === i && step.action === 'try' ? ' used-highlight' : ''}`}
              >
                {i}:{u ? 'T' : 'F'}
              </div>
            ))}
          </div>
        </div>

        {/* Result display */}
        <div className="state-section">
          <span className="state-section-label">
            📦 已收集结果（{step.result.length} 个排列）
          </span>
          <div className="result-section">
            {step.result.length === 0 ? (
              <div className="result-empty">暂无结果</div>
            ) : (
              <div className="result-grid">
                {step.result.map((perm, i) => {
                  const isNew = isCompleteAction && i === step.result.length - 1;
                  return (
                    <span key={i} className={`result-item${isNew ? ' newest' : ''}`}>
                      [{perm.join(', ')}]
                    </span>
                  );
                })}
                <div ref={resultEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
