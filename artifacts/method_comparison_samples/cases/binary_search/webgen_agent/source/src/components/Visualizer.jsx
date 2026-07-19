import React from 'react';
import './Visualizer.css';

export default function Visualizer({
  nums, target, step, currentStep, totalSteps,
  onPrev, onNext, onReset, onShowAnswer, onHint,
  onStepChange, isFirstStep, isLastStep, showAnswer,
  hintVisible, hintLevel
}) {
  const getElementClass = (index) => {
    const classes = ['viz-element'];
    if (step.phase === 'init') {
      if (index >= step.left && index <= step.right) classes.push('in-range');
    } else if (step.phase === 'found' && index === step.mid) {
      classes.push('found');
    } else if (step.phase === 'discardLeft') {
      if (index >= (step.oldLeft || 0) && index <= step.mid) classes.push('discarded');
      else if (index >= step.left && index <= step.right) classes.push('in-range');
    } else if (step.phase === 'discardRight') {
      if (index >= step.mid && index <= (step.oldRight || nums.length - 1)) classes.push('discarded');
      else if (index >= step.left && index <= step.right) classes.push('in-range');
    } else {
      if (index >= step.left && index <= step.right) classes.push('in-range');
      if (index === step.mid) classes.push('mid');
    }
    return classes.join(' ');
  };

  const getPointerLabel = (index) => {
    const labels = [];
    if (index === step.left && step.phase !== 'init') labels.push('L');
    if (index === step.right && step.phase !== 'init') labels.push('R');
    if (index === step.mid && step.phase !== 'init' && step.phase !== 'found') labels.push('M');
    if (step.phase === 'found' && index === step.mid) labels.push('✓');
    return labels;
  };

  const humanStep = currentStep + 1;
  const totalHumanSteps = totalSteps;

  return (
    <div className="visualizer">
      <div className="viz-header">
        <h3 className="section-title">🔍 算法可视化</h3>
        <span className="step-counter">步骤 {humanStep} / {totalHumanSteps}</span>
      </div>

      <div className="array-viz">
        {nums.map((num, i) => (
          <div key={i} className={getElementClass(i)}>
            <div className="pointer-labels">
              {getPointerLabel(i).map((l, j) => (
                <span key={j} className={`pointer-label pointer-${l.toLowerCase()}`}>{l}</span>
              ))}
            </div>
            <div className="element-card">
              <span className="element-value">{num}</span>
            </div>
            <span className="element-index">{i}</span>
          </div>
        ))}
      </div>

      <div className="viz-legend">
        <span className="legend-item"><span className="legend-dot in-range"></span> 搜索区间</span>
        <span className="legend-item"><span className="legend-dot mid"></span> 中点 (mid)</span>
        <span className="legend-item"><span className="legend-dot discarded"></span> 已丢弃</span>
        <span className="legend-item"><span className="legend-dot found"></span> 找到</span>
      </div>

      <div className="step-description">
        <p>{step.description}</p>
      </div>

      {hintVisible && (
        <div className="hint-box">
          <span className="hint-icon">💡</span>
          <span>提示级别 {hintLevel}/4</span>
        </div>
      )}

      <div className="viz-controls">
        <div className="nav-buttons">
          <button onClick={onReset} className="btn btn-outline" title="回到初始状态">
            ⟳ 重置
          </button>
          <button onClick={onPrev} disabled={isFirstStep} className="btn btn-nav" title="上一步">
            ◀ 上一步
          </button>
          <button onClick={onNext} disabled={isLastStep} className="btn btn-play" title="下一步">
            {isFirstStep ? '▶ 开始' : '下一步 ▶'}
          </button>
        </div>

        <div className="slider-row">
          <span className="slider-label">跳转:</span>
          <input
            type="range"
            min={0}
            max={totalSteps - 1}
            value={currentStep}
            onChange={(e) => onStepChange(parseInt(e.target.value))}
            className="step-slider"
          />
          <span className="slider-value">{humanStep}</span>
        </div>

        <div className="action-buttons">
          <button onClick={onHint} className="btn btn-hint" title="获取逐步提示">
            💡 提示
          </button>
          <button onClick={onShowAnswer} className="btn btn-answer" disabled={showAnswer} title="查看最终答案">
            {showAnswer ? '✓ 已显示' : '👁 显示答案'}
          </button>
        </div>
      </div>
    </div>
  );
}
