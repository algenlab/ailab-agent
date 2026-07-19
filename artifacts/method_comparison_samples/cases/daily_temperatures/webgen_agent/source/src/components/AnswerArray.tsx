import React from 'react';

interface AnswerArrayProps {
  answerState: number[];
  expectedAnswer: number[];
  showFinalAnswer: boolean;
  isComplete: boolean;
}

export const AnswerArray: React.FC<AnswerArrayProps> = ({
  answerState,
  expectedAnswer,
  showFinalAnswer,
  isComplete,
}) => {
  const allZero = answerState.every((v) => v === 0);

  return (
    <div className="card p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        📝 Answer 数组
      </h3>
      {allZero && !isComplete && !showFinalAnswer ? (
        <div className="flex flex-col items-center justify-center h-28 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50/50">
          <span className="text-3xl mb-2 opacity-40">📋</span>
          <span className="text-sm">答案待计算</span>
          <span className="text-xs text-gray-300 mt-1">扫描温度数组后将逐步填充…</span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 justify-center">
          {answerState.map((val, idx) => {
            const isExpected = showFinalAnswer || isComplete;
            const displayVal = isExpected ? expectedAnswer[idx] : val;
            const isSet = val > 0;
            const isZero = val === 0 && (isComplete || showFinalAnswer);
            return (
              <div
                key={idx}
                className="w-14 h-14 flex flex-col items-center justify-center rounded-lg border-2 transition-all duration-300 animate-fade-in"
                style={{
                  backgroundColor: isSet
                    ? '#ecfdf5'
                    : isZero
                    ? '#f9fafb'
                    : '#f3f4f6',
                  borderColor: isSet
                    ? '#6ee7b7'
                    : isZero
                    ? '#d1d5db'
                    : '#e5e7eb',
                }}
              >
                <span className="text-[10px] text-gray-400">[{idx}]</span>
                <span
                  className={`font-mono font-bold ${
                    isSet ? 'text-emerald-700' : 'text-gray-600'
                  }`}
                >
                  {displayVal}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {showFinalAnswer && (
        <div className="mt-3 text-center text-sm text-emerald-700 bg-emerald-50 py-2 rounded-lg animate-slide-up font-medium">
          ✅ 最终正确答案：<span className="font-mono font-bold">[{expectedAnswer.join(', ')}]</span>
        </div>
      )}
    </div>
  );
};
