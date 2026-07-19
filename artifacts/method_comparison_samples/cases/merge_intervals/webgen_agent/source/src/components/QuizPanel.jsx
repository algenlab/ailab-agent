import React, { useState } from 'react';
import { quizQuestions } from '../data';

export default function QuizPanel({ quizState, onAnswer, onShowAnswer, onHint }) {
  const [activeQ, setActiveQ] = useState(0);

  const hintsMap = {
    q1: '考虑：当前区间起点 2 与 merged 最后区间终点 3 的大小关系。2 ≤ 3 意味着重叠。',
    q2: '不变式要求 merged 中区间互不重叠且右端点正确。检查 [1,3] 在处理 [2,3] 后是否可能。',
    q3: '分析原合并结果 [[1,6],[8,10]]，要变成 [[1,6],[8,9]]，只需修改最后一个区间的右端点。',
    q4: '判断重叠的关键条件：curr[0] ≤ lastMerged[1]。这里 4 ≤ 3 成立吗？',
  };

  const question = quizQuestions[activeQ];
  const state = quizState[question.id] || {};

  const handleSelect = (key) => {
    if (state.revealed || state.status === 'correct' || state.status === 'wrong') return;
    onAnswer(question.id, key, question.correctKey, question.explanation);
  };

  const handleReveal = () => {
    if (state.revealed) return;
    onShowAnswer(question.id, question.correctKey, question.explanation);
  };

  const handleHintClick = () => {
    onHint(question.id, hintsMap[question.id] || '请仔细思考问题。');
  };

  const isAnswered = state.status === 'correct' || state.status === 'wrong' || state.revealed;

  return (
    <div className="card">
      <div className="card-header">
        <span className="icon">🧠</span>
        <h2>学习者检测</h2>
      </div>

      {/* Question selector tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {quizQuestions.map((q, i) => {
          const st = quizState[q.id] || {};
          let dot = '⚪';
          if (st.status === 'correct') dot = '🟢';
          else if (st.status === 'wrong') dot = '🔴';
          else if (st.revealed) dot = '🟡';
          return (
            <button
              key={q.id}
              className={`btn btn-sm ${i === activeQ ? 'btn-primary' : ''}`}
              onClick={() => setActiveQ(i)}
              style={{ fontSize: '0.74rem' }}
            >
              {dot} 问题 {i + 1}
            </button>
          );
        })}
      </div>

      {/* Question content */}
      <div className="quiz-block">
        <div className="quiz-question">
          {question.question}
        </div>

        <div className="quiz-options">
          {question.options.map((opt) => {
            let optCls = 'quiz-option';
            if (state.selected === opt.key) {
              optCls += ' selected';
              if (state.status === 'correct') optCls += ' correct';
              else if (state.status === 'wrong') optCls += ' wrong';
            }
            if (state.revealed && opt.key === question.correctKey) {
              optCls += ' correct';
            }
            return (
              <button
                key={opt.key}
                className={optCls}
                onClick={() => handleSelect(opt.key)}
                disabled={!!state.revealed}
              >
                {opt.key}. {opt.text}
              </button>
            );
          })}
        </div>

        {/* Feedback */}
        {state.status === 'correct' && !state.revealed && (
          <div className="feedback-banner correct">
            ✅ 回答正确！{question.explanation}
          </div>
        )}
        {state.status === 'wrong' && !state.revealed && (
          <div className="feedback-banner wrong">
            ❌ 回答错误。{question.explanation}
          </div>
        )}
        {state.revealed && (
          <div className="feedback-banner correct" style={{ background: '#fef3c7', color: '#92400e' }}>
            💡 已查看答案：{question.explanation}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <button
            className="btn btn-sm"
            onClick={handleHintClick}
            style={{
              background: '#fffbeb',
              borderColor: '#f59e0b',
              color: '#b45309',
            }}
          >
            💡 提示
          </button>
          {!isAnswered && (
            <button
              className="btn btn-sm"
              onClick={handleReveal}
              style={{
                background: '#f8f9fb',
                borderColor: '#c4cad4',
                color: '#374151',
              }}
            >
              👁 显示答案
            </button>
          )}
          {isAnswered && (
            <button
              className="btn btn-sm"
              disabled
              style={{
                background: '#f8f9fb',
                borderColor: '#e1e5eb',
                color: '#9ca3af',
                cursor: 'default',
              }}
            >
              👁 显示答案
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
