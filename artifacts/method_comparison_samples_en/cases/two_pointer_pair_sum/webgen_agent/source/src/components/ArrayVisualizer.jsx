import React from 'react';

export default function ArrayVisualizer({ nums, leftIdx, rightIdx, sum, target, compareResult, isFound, actionText, stepId }) {
  const getCellClass = (index) => {
    const classes = ['array-cell'];
    if (index === leftIdx && index === rightIdx) {
      classes.push('cell-both');
    } else if (index === leftIdx) {
      classes.push('cell-left');
    } else if (index === rightIdx) {
      classes.push('cell-right');
    }
    if (isFound && (index === leftIdx || index === rightIdx)) {
      classes.push('cell-found');
    }
    return classes.join(' ');
  };

  const getPointerLabel = (index) => {
    const labels = [];
    if (index === leftIdx) labels.push('L');
    if (index === rightIdx) labels.push('R');
    return labels.join(' / ');
  };

  const getCompareSymbol = () => {
    switch (compareResult) {
      case 'greater': return '>';
      case 'less': return '<';
      case 'equal': return '=';
      default: return '?';
    }
  };

  const getCompareClass = () => {
    switch (compareResult) {
      case 'greater': return 'compare-greater';
      case 'less': return 'compare-less';
      case 'equal': return 'compare-equal';
      default: return '';
    }
  };

  return (
    <div className="array-visualizer" role="region" aria-label="Array visualization with two pointers">
      <div className="step-badge">Step {stepId} / 2</div>

      <div className="array-container">
        {nums.map((value, index) => (
          <div key={index} className={getCellClass(index)}>
            <span className="cell-index">{index}</span>
            <span className="cell-value">{value}</span>
            {(index === leftIdx || index === rightIdx) && (
              <span className="cell-pointer-label" aria-label={`Pointer ${getPointerLabel(index)}`}>
                {getPointerLabel(index)}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="sum-display" aria-live="polite">
        <div className="sum-equation">
          <span className={`sum-left-val ${leftIdx >= 0 ? 'highlight-left' : ''}`}>
            nums[{leftIdx}] = {leftIdx >= 0 ? nums[leftIdx] : '?'}
          </span>
          <span className="sum-operator">+</span>
          <span className={`sum-right-val ${rightIdx >= 0 ? 'highlight-right' : ''}`}>
            nums[{rightIdx}] = {rightIdx >= 0 ? nums[rightIdx] : '?'}
          </span>
          <span className="sum-operator">=</span>
          <span className="sum-result">{sum}</span>
        </div>
        <div className={`sum-comparison ${getCompareClass()}`}>
          <span className="comparison-text">
            {sum} {getCompareSymbol()} {target} (target)
          </span>
          <span className="comparison-arrow">
            {compareResult === 'greater' && '→ move right pointer left'}
            {compareResult === 'less' && '→ move left pointer right'}
            {compareResult === 'equal' && '→ match found!'}
          </span>
        </div>
      </div>

      <div className="action-description" aria-live="polite">
        <p>{actionText}</p>
      </div>

      {isFound && (
        <div className="found-banner" role="alert">
          <span className="found-icon">✓</span>
          Solution found: indices <strong>[{leftIdx}, {rightIdx}]</strong> — prices {nums[leftIdx]} + {nums[rightIdx]} = {target}
        </div>
      )}
    </div>
  );
}