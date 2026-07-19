import React from 'react';
import { QUESTIONS } from '../data';

export function QuizPanel({
  activeQuiz, setActiveQuiz, quizAnswers, quizFeedback,
  showHints, showAnswers, onSelect, onHint, onShowAnswer
}) {
  const q = QUESTIONS[activeQuiz];

  return (
    <div className="card full-width">
      <h2>🎯 学习检测</h2>

      {/* Tab bar */}
      <div className="tab-bar">
        {QUESTIONS.map((_, i) => (
          <div
            key={i}
            className={`tab ${activeQuiz === i ? 'active' : ''}`}
            onClick={() => setActiveQuiz(i)}
          >
            Q{i + 1}
            {quizFeedback[i] === 'correct' && ' ✅'}
            {quizFeedback[i] === 'incorrect' && ' ❌'}
          </div>
        ))}
      </div>

      {/* Active question */}
      <div className={`quiz-block ${quizFeedback[activeQuiz] === undefined ? 'active' : ''}`}>
        <div className="quiz-question">
          {activeQuiz + 1}. {q.question}
        </div>

        <div className="quiz-options">
          {q.options.map((opt, i) => {
            let cls = 'quiz-option';
            if (quizAnswers[activeQuiz] === i) {
              cls += ' selected';
              if (quizFeedback[activeQuiz] === 'correct') cls += ' correct';
              else if (quizFeedback[activeQuiz] === 'incorrect') cls += ' incorrect';
            }
            return (
              <button
                key={i}
                className={cls}
                onClick={() => onSelect(activeQuiz, i)}
                disabled={quizFeedback[activeQuiz] !== undefined}
              >
                {opt}
              </button>
            );
          })}
        </div>

        {/* Feedback */}
        {quizFeedback[activeQuiz] === 'correct' && (
          <div className="feedback correct">✅ 正确！你理解得很到位。</div>
        )}
        {quizFeedback[activeQuiz] === 'incorrect' && (
          <div className="feedback incorrect">
            ❌ 不正确。正确答案是: <strong>{q.answer}</strong>
          </div>
        )}

        {/* Hint / Show Answer */}
        {showHints[activeQuiz] && (
          <div className="feedback" style={{ background: 'var(--warning-light)', color: 'var(--warning)', border: '1px solid var(--warning)' }}>
            💡 {q.hint}
          </div>
        )}
        {showAnswers[activeQuiz] && quizFeedback[activeQuiz] === undefined && (
          <div className="feedback" style={{ background: 'var(--primary-light)', color: 'var(--primary-dark)', border: '1px solid var(--primary)' }}>
            📖 答案: <strong>{q.answer}</strong>
          </div>
        )}

        {/* Action Buttons */}
        <div className="action-row">
          <button className="btn btn-warning btn-sm" onClick={() => onHint(activeQuiz)}>
            💡 提示
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => onShowAnswer(activeQuiz)}
            disabled={quizFeedback[activeQuiz] !== undefined}
          >
            📖 显示答案
          </button>
        </div>
      </div>
    </div>
  );
}
