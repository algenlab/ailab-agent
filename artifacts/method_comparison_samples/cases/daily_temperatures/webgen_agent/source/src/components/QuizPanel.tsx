import React, { useState } from 'react';
import { QuizState } from '../types';

interface QuizPanelProps {
  quizState: QuizState;
  sliderValue: number;
  sliderModified: boolean;
  modifiedAnswer: number | null;
  onSubmitQ1: (answer: string) => void;
  onSubmitQ2: (answer: string) => void;
  onSubmitQ3: (answer: string) => void;
  onRevealQ4: () => void;
  onSliderChange: (value: number) => void;
}

export const QuizPanel: React.FC<QuizPanelProps> = ({
  quizState,
  sliderValue,
  sliderModified,
  modifiedAnswer,
  onSubmitQ1,
  onSubmitQ2,
  onSubmitQ3,
  onRevealQ4,
  onSliderChange,
}) => {
  const [q1Answer, setQ1Answer] = useState('');
  const [q2Answer, setQ2Answer] = useState('');
  const [q3Answer, setQ3Answer] = useState('');

  return (
    <div className="card p-4 sm:p-6 space-y-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        🎯 学习者检测
      </h3>

      {/* Question 1 */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
        <p className="font-medium text-gray-800">
          1. 当前正要处理温度 <strong>75°C（下标 2）</strong>，此时栈顶是下标 1（对应 74°C）。下一步会执行什么操作？
        </p>
        <div className="flex flex-wrap gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="q1"
              value="A"
              checked={q1Answer === 'A'}
              onChange={(e) => setQ1Answer(e.target.value)}
              disabled={quizState.q1Answered}
              className="text-emerald-600"
            />
            <span>A. 弹出栈顶并写入 answer</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="q1"
              value="B"
              checked={q1Answer === 'B'}
              onChange={(e) => setQ1Answer(e.target.value)}
              disabled={quizState.q1Answered}
              className="text-emerald-600"
            />
            <span>B. 压入当前下标</span>
          </label>
        </div>
        {!quizState.q1Answered && (
          <button
            onClick={() => q1Answer && onSubmitQ1(q1Answer)}
            disabled={!q1Answer}
            className="btn-primary text-sm"
          >
            提交答案
          </button>
        )}
        {quizState.q1Answered && (
          <div
            className={`text-sm font-medium px-3 py-2 rounded ${
              quizState.q1Correct
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {quizState.q1Correct
              ? '✅ 正确！75°C > 74°C（栈顶），应弹出栈顶并写入 answer[1] = 1。'
              : '❌ 错误。75°C > 74°C（栈顶温度），根据单调栈规则，应弹出栈顶并计算等待天数。'}
          </div>
        )}
      </div>

      {/* Question 2 */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
        <p className="font-medium text-gray-800">
          2. 在整个扫描过程中，关于栈的状态，以下哪项是正确的？
        </p>
        <div className="flex flex-col gap-2">
          {['A. 栈内（底→顶）温度值单调递减', 'B. 栈内（底→顶）温度值单调递增', 'C. 栈内下标对应温度随机排列'].map(
            (option) => (
              <label
                key={option[0]}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="radio"
                  name="q2"
                  value={option[0]}
                  checked={q2Answer === option[0]}
                  onChange={(e) => setQ2Answer(e.target.value)}
                  disabled={quizState.q2Answered}
                  className="text-emerald-600"
                />
                <span>{option}</span>
              </label>
            )
          )}
        </div>
        {!quizState.q2Answered && (
          <button
            onClick={() => q2Answer && onSubmitQ2(q2Answer)}
            disabled={!q2Answer}
            className="btn-primary text-sm"
          >
            提交答案
          </button>
        )}
        {quizState.q2Answered && (
          <div
            className={`text-sm font-medium px-3 py-2 rounded ${
              quizState.q2Correct
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {quizState.q2Correct
              ? '✅ 正确！单调栈的核心不变式：栈内从底到顶的下标对应温度值严格单调递减。'
              : '❌ 错误。保持栈内温度单调递减才能确保遇到更高温度时，栈顶元素最先被处理。'}
          </div>
        )}
      </div>

      {/* Question 3 */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
        <p className="font-medium text-gray-800">
          3. 将第 4 天温度由 69°C 改为 {sliderValue}°C，预测 answer[4] 的等待天数会如何变化？
        </p>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">69°C</span>
          <input
            type="range"
            min={65}
            max={75}
            step={1}
            value={sliderValue}
            onChange={(e) => onSliderChange(Number(e.target.value))}
            className="flex-1 accent-emerald-600"
          />
          <span
            className={`text-sm font-bold font-mono ${
              sliderValue !== 69 ? 'text-amber-600' : 'text-gray-600'
            }`}
          >
            {sliderValue}°C
          </span>
        </div>
        {sliderModified && modifiedAnswer !== null && (
          <div className="text-sm bg-blue-50 text-blue-700 px-3 py-2 rounded animate-slide-up">
            修改后 answer[4] = <span className="font-mono font-bold">{modifiedAnswer}</span>
            {modifiedAnswer === 1 ? '（与原始答案相同）' : '（已改变）'}
          </div>
        )}
        <p className="text-sm text-gray-600">
          当改为 71°C 时，请选择你的预测：
        </p>
        <div className="flex flex-wrap gap-3">
          {[
            { value: 'increase', label: 'A. answer[4] 增大' },
            { value: 'decrease', label: 'B. answer[4] 减小' },
            { value: 'same', label: 'C. answer[4] 不变' },
          ].map((opt) => (
            <label
              key={opt.value}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="radio"
                name="q3"
                value={opt.value}
                checked={q3Answer === opt.value}
                onChange={(e) => setQ3Answer(e.target.value)}
                disabled={quizState.q3Answered}
                className="text-emerald-600"
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
        {!quizState.q3Answered && (
          <button
            onClick={() => q3Answer && onSubmitQ3(q3Answer)}
            disabled={!q3Answer}
            className="btn-primary text-sm"
          >
            提交预测
          </button>
        )}
        {quizState.q3Answered && (
          <div
            className={`text-sm font-medium px-3 py-2 rounded ${
              quizState.q3Correct
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {quizState.q3Correct
              ? '✅ 正确！69°C → 71°C，answer[4] 仍为 1（因为 72°C 依然高于 71°C，仍然会在同一天被弹出）。'
              : '❌ 错误。69°C → 71°C 后，answer[4] 仍为 1，因为下标 5 的 72°C 仍然高于 71°C，等待天数不变。'}
          </div>
        )}
      </div>

      {/* Question 4 */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
        <p className="font-medium text-gray-800">
          4. 处理温度 72°C（下标 5）时，先后弹出了下标 3（71°C）和 4（69°C），请解释为什么弹出两个下标？
        </p>
        {!quizState.q4Revealed ? (
          <button onClick={onRevealQ4} className="btn-outline text-sm">
            查看参考答案
          </button>
        ) : (
          <div className="text-sm bg-emerald-50 text-emerald-800 px-3 py-2 rounded animate-slide-up leading-relaxed">
            <strong>参考答案：</strong>
            因为 72°C 同时高于栈顶元素 69°C（下标 4）和次栈顶元素 71°C（下标 3）。
            根据单调栈规则，当前温度高于栈顶时持续弹出，直到栈顶温度 ≥ 当前温度或栈为空。
            每次弹出意味着找到了该下标对应的"下一个更高温度"，弹出两个下标说明 72°C 同时是下标 4 和下标 3 的"下一个更高温度"，
            等待天数分别为 5−4=1 和 5−3=2。
          </div>
        )}
      </div>
    </div>
  );
};
