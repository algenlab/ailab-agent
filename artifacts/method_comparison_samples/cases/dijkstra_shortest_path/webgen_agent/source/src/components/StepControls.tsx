import React from 'react';

interface Props {
  stepIndex: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
  onReset: () => void;
  onAutoPlay: () => void;
  isAutoPlaying: boolean;
}

const StepControls: React.FC<Props> = ({
  stepIndex,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  onAutoPlay,
  isAutoPlaying,
}) => {
  return (
    <div className="step-controls">
      <span className="step-indicator">
        步骤 {stepIndex + 1}/{totalSteps}
      </span>
      <button className="btn btn-sm" onClick={onReset} disabled={stepIndex === 0}>
        ⏮ 重置
      </button>
      <button className="btn btn-sm" onClick={onPrev} disabled={stepIndex === 0}>
        ◀ 上一步
      </button>
      <button
        className="btn btn-sm"
        onClick={onNext}
        disabled={stepIndex >= totalSteps - 1}
      >
        下一步 ▶
      </button>
      <button
        className={`btn btn-sm ${isAutoPlaying ? 'btn-warning' : 'btn-primary'}`}
        onClick={onAutoPlay}
      >
        {isAutoPlaying ? '⏸ 暂停' : '▶ 自动播放'}
      </button>
    </div>
  );
};

export default StepControls;
