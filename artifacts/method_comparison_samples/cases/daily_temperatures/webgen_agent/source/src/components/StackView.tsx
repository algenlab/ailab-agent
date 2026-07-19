import React from 'react';

interface StackViewProps {
  stack: number[];
  temperatures: number[];
  pops: { index: number; answerValue: number }[];
  isProcessing: boolean;
}

export const StackView: React.FC<StackViewProps> = ({
  stack,
  temperatures,
  pops,
  isProcessing,
}) => {
  return (
    <div className="card p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        📚 单调栈（存储下标）
      </h3>
      {stack.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-28 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50/50">
          <span className="text-3xl mb-2 opacity-40">📭</span>
          <span className="text-sm">栈为空</span>
          <span className="text-xs text-gray-300 mt-1">等待元素入栈…</span>
        </div>
      ) : (
        <div className="flex flex-col-reverse gap-1">
          {stack.map((idx, pos) => {
            const isTop = pos === stack.length - 1;
            return (
              <div
                key={idx}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 transition-all duration-300 animate-slide-up ${
                  isTop
                    ? 'bg-blue-100 border-blue-500 shadow-sm'
                    : 'bg-blue-50 border-blue-300'
                }`}
              >
                <span className="text-xs text-gray-400 font-mono w-6">
                  {isTop ? '栈顶→' : `  [${pos}]`}
                </span>
                <span className="font-mono font-bold text-blue-800">
                  下标 {idx}
                </span>
                <span className="text-blue-600 text-sm">({temperatures[idx]}°C)</span>
                {isTop && isProcessing && (
                  <span className="ml-auto text-amber-500 text-xs animate-pulse font-medium">
                    比较中…
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
      {pops.length > 0 && (
        <div className="mt-3 space-y-1">
          <div className="text-xs text-gray-500 font-medium mb-1">🔔 本次弹出：</div>
          {pops.map((pop) => (
            <div
              key={pop.index}
              className="text-sm text-orange-600 bg-orange-50 px-3 py-1 rounded border border-orange-200 animate-slide-up"
            >
              弹出下标 <span className="font-mono font-bold">{pop.index}</span> ({temperatures[pop.index]}°C)
              → answer[{pop.index}] = <span className="font-mono font-bold">{pop.answerValue}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
