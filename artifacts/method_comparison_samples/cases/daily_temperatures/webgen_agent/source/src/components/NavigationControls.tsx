import React, { useEffect } from 'react';

interface NavigationControlsProps {
  currentStepIndex: number;
  maxStepIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onReset: () => void;
  onRevealHint: () => void;
  onRevealAnswer: () => void;
  hintsRevealed: number;
  showFinalAnswer: boolean;
}

const HINTS = [
  '提示 1：观察栈中存储的是下标，且栈内下标对应的温度值保持怎样的顺序？',
  '提示 2：当前温度高于栈顶温度时，说明找到了栈顶下标对应的"更高温度"，应该弹出栈顶并计算等待天数。',
  '提示 3：弹出后计算等待天数 = 当前下标 − 弹出下标，写入 answer 对应位置。若当前温度 ≤ 栈顶温度，则压入当前下标。',
];

export const NavigationControls: React.FC<NavigationControlsProps> = ({
  currentStepIndex,
  maxStepIndex,
  onPrev,
  onNext,
  onReset,
  onRevealHint,
  onRevealAnswer,
  hintsRevealed,
  showFinalAnswer,
}) => {
  const progressPercent =
    maxStepIndex > 0
      ? Math.round((currentStepIndex / maxStepIndex) * 100)
      : 0;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        onNext();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        onPrev();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNext, onPrev]);

  return (
    <div className="card p-4 sm:p-6 space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 font-mono">
          步骤 {currentStepIndex} / {maxStepIndex}
        </span>
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{progressPercent}%</span>
      </div>

      <div className="flex flex-wrap gap-2 justify-center">
        <button
          onClick={onPrev}
          disabled={currentStepIndex === 0}
          className="btn-secondary text-sm"
        >
          ◀ 上一步
        </button>
        <button
          onClick={onNext}
          disabled={currentStepIndex >= maxStepIndex}
          className="btn-primary text-sm"
        >
          下一步 ▶
        </button>
        <button onClick={onReset} className="btn-secondary text-sm">
          🔄 重置
        </button>
        <button
          onClick={onRevealHint}
          disabled={hintsRevealed >= 3}
          className="btn-outline text-sm"
        >
          💡 提示 {hintsRevealed > 0 ? `(${hintsRevealed}/3)` : ''}
        </button>
        <button
          onClick={onRevealAnswer}
          disabled={showFinalAnswer}
          className="btn-outline text-sm"
        >
          👁️ {showFinalAnswer ? '已显示' : '显示答案'}
        </button>
      </div>

      {hintsRevealed > 0 && (
        <div className="space-y-1">
          {HINTS.slice(0, hintsRevealed).map((hint, idx) => (
            <div
              key={idx}
              className="text-sm bg-amber-50 text-amber-800 px-3 py-2 rounded border border-amber-200 animate-slide-up"
            >
              {hint}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 text-center">
        提示：使用键盘 ← → 方向键可快速导航步骤
      </p>
    </div>
  );
};
