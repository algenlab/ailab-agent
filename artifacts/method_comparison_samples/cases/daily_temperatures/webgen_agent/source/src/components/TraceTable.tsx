import React, { useEffect, useRef } from 'react';
import { AlgorithmStep } from '../types';

interface TraceTableProps {
  steps: AlgorithmStep[];
  currentStepIndex: number;
  temperatures: number[];
  onStepClick: (index: number) => void;
}

export const TraceTable: React.FC<TraceTableProps> = ({
  steps,
  currentStepIndex,
  temperatures,
  onStepClick,
}) => {
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  useEffect(() => {
    rowRefs.current[currentStepIndex]?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    });
  }, [currentStepIndex]);

  return (
    <div className="card overflow-hidden">
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          📋 算法 Trace 表
        </h3>
        <span className="text-xs text-gray-400">
          共 {steps.length} 步（含初始状态）
        </span>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr className="text-left text-xs text-gray-500 uppercase">
              <th className="px-3 py-2 w-12">步骤</th>
              <th className="px-3 py-2 w-20">当前</th>
              <th className="px-3 py-2 w-32">栈(前)</th>
              <th className="px-3 py-2">操作</th>
              <th className="px-3 py-2 w-32">栈(后)</th>
              <th className="px-3 py-2 w-44">Answer</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step, idx) => {
              const isCurrent = idx === currentStepIndex;
              return (
                <tr
                  key={step.id}
                  ref={(el) => {
                    rowRefs.current[idx] = el;
                  }}
                  onClick={() => onStepClick(idx)}
                  className={`cursor-pointer transition-colors border-b border-gray-50 ${
                    isCurrent
                      ? 'bg-amber-50 ring-1 ring-amber-300'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="px-3 py-2 font-mono text-center">
                    <span
                      className={`inline-flex w-7 h-7 items-center justify-center rounded-full text-xs font-bold ${
                        isCurrent
                          ? 'bg-amber-500 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {step.id}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {step.processingIndex >= 0 ? (
                      <>
                        <span className="font-bold">[{step.processingIndex}]</span>{' '}
                        {step.processingTemp}°C
                      </>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {step.stackBefore.length === 0 ? (
                      <span className="text-gray-400">[]</span>
                    ) : (
                      <span>
                        [{step.stackBefore.join(', ')}]
                        <br />
                        <span className="text-gray-400">
                          [{step.stackBefore.map((i) => temperatures[i]).join('°, ')}°]
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs leading-relaxed max-w-xs">
                    {step.description}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {step.stackAfter.length === 0 ? (
                      <span className="text-gray-400">[]</span>
                    ) : (
                      <span>
                        [{step.stackAfter.join(', ')}]
                        <br />
                        <span className="text-gray-400">
                          [{step.stackAfter.map((i) => temperatures[i]).join('°, ')}°]
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    [{step.answerState.join(', ')}]
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
