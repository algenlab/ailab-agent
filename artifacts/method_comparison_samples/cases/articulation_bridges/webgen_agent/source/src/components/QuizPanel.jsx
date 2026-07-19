import React, { useState } from 'react';

export default function QuizPanel({ questions, onAnswer, activityLog }) {
  const [currentQ, setCurrentQ] = useState(0);
  const [selected, setSelected] = useState(null);
  const [answered, setAnswered] = useState({});
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  const question = questions[currentQ];
  const isAnswered = answered[currentQ] !== undefined;

  function handleSelect(option) {
    if (isAnswered) return;
    setSelected(option.label);
    const correct = option.correct;
    setAnswered({ ...answered, [currentQ]: correct });
    onAnswer({
      questionId: question.id,
      question: question.question,
      selectedAnswer: option.text,
      correct,
      timestamp: new Date().toLocaleTimeString()
    });
    setShowHint(false);
    setShowAnswer(false);
  }

  function handleHint() {
    setShowHint(true);
    onAnswer({
      questionId: question.id,
      question: question.question,
      action: 'hint',
      timestamp: new Date().toLocaleTimeString()
    });
  }

  function handleShowAnswer() {
    setShowAnswer(true);
    const correctOption = question.options.find(o => o.correct);
    setSelected(correctOption.label);
    setAnswered({ ...answered, [currentQ]: true });
    onAnswer({
      questionId: question.id,
      question: question.question,
      action: 'show-answer',
      correctAnswer: correctOption.text,
      timestamp: new Date().toLocaleTimeString()
    });
  }

  function goToQuestion(idx) {
    setCurrentQ(idx);
    setSelected(answered[idx] !== undefined ? (answered[idx] ? question.options.find(o => o.correct)?.label : 'X') : null);
    setShowHint(false);
    setShowAnswer(false);
  }

  return (
    <div className="quiz-panel">
      <h3>📝 学习检测 ({currentQ + 1}/{questions.length})</h3>

      <div className="quiz-nav-tabs">
        {questions.map((q, i) => (
          <button
            key={q.id}
            className={`quiz-tab ${i === currentQ ? 'active' : ''} ${answered[i] === true ? 'correct-tab' : answered[i] === false ? 'incorrect-tab' : ''}`}
            onClick={() => goToQuestion(i)}
          >
            Q{i + 1}
          </button>
        ))}
      </div>

      <div className="quiz-question">
        <p>{question.question}</p>
      </div>

      <div className="quiz-options">
        {question.options.map((opt) => {
          let cls = 'quiz-option';
          if (isAnswered || showAnswer) {
            if (opt.correct) cls += ' option-correct';
            else if (selected === opt.label && !opt.correct) cls += ' option-incorrect';
          } else if (selected === opt.label) {
            cls += ' option-selected';
          }
          return (
            <button
              key={opt.label}
              className={cls}
              onClick={() => handleSelect(opt)}
              disabled={isAnswered || showAnswer}
            >
              <span className="option-label">{opt.label}</span>
              <span className="option-text">{opt.text}</span>
              {isAnswered && opt.correct && <span className="option-icon">✓</span>}
              {isAnswered && selected === opt.label && !opt.correct && <span className="option-icon">✗</span>}
            </button>
          );
        })}
      </div>

      <div className="quiz-actions">
        <button className="action-btn hint-btn" onClick={handleHint} disabled={isAnswered}>
          💡 提示
        </button>
        <button className="action-btn answer-btn" onClick={handleShowAnswer} disabled={isAnswered}>
          👁 显示答案
        </button>
      </div>

      {showHint && (
        <div className="feedback hint-feedback">
          <strong>💡 提示：</strong> 回顾 DFS 的邻接表遍历顺序，以及 low 数组的更新规则。思考 low[v] 与 dfn[u] 的比较含义。
        </div>
      )}

      {isAnswered && (
        <div className={`feedback ${answered[currentQ] ? 'correct-feedback' : 'incorrect-feedback'}`}>
          <strong>{answered[currentQ] ? '✅ 回答正确！' : '❌ 回答错误'}</strong>
          <p>{question.explanation}</p>
        </div>
      )}

      {showAnswer && !isAnswered && (
        <div className="feedback correct-feedback">
          <strong>👁 答案：</strong>
          <p>{question.explanation}</p>
        </div>
      )}
    </div>
  );
}