import React from 'react';
import { CellState } from '../types';

interface TemperatureArrayProps {
  temperatures: number[];
  cellStates: CellState[];
  currentIndex: number;
  answerState: number[];
}

const stateStyles: Record<CellState, string> = {
  pending: 'bg-gray-100 text-gray-500 border-gray-200',
  current:
    'bg-amber-100 text-amber-800 border-amber-400 ring-2 ring-amber-400 shadow-md scale-105 z-10',
  'in-stack': 'bg-blue-100 text-blue-700 border-blue-400',
  resolved: 'bg-emerald-100 text-emerald-700 border-emerald-400',
  'no-answer': 'bg-gray-200 text-gray-600 border-gray-300',
};

const stateLabels: Record<CellState, string> = {
  pending: '待处理',
  current: '当前',
  'in-stack': '栈中',
  resolved: '已解决',
  'no-answer': '无更高温度',
};

export const TemperatureArray: React.FC<TemperatureArrayProps> = ({
  temperatures,
  cellStates,
  currentIndex,
  answerState,
}) => {
  return (
    <div className="card p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        🌡️ 温度数组
      </h3>
      <div className="flex flex-wrap gap-2 justify-center">
        {temperatures.map((temp, idx) => {
          const state = cellStates[idx];
          return (
            <div key={idx} className="flex flex-col items-center gap-1 animate-fade-in">
              <div className={`temp-cell ${stateStyles[state]}`}>
                <span className="text-xs text-gray-400">{idx}</span>
                <span>{temp}°</span>
              </div>
              {state === 'resolved' && answerState[idx] > 0 && (
                <span className="text-xs text-emerald-600 font-mono font-bold animate-slide-up">
                  等{answerState[idx]}天
                </span>
              )}
              {state === 'no-answer' && (
                <span className="text-xs text-gray-400 font-mono animate-slide-up">0天</span>
              )}
              <span className="text-[10px] text-gray-400">{stateLabels[state]}</span>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 justify-center mt-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-gray-100 border border-gray-200" /> 待处理
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-amber-100 border border-amber-400" /> 当前
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-blue-100 border border-blue-400" /> 栈中
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-400" /> 已解决
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-gray-200 border border-gray-300" /> 无更高温度
        </span>
      </div>
    </div>
  );
};
