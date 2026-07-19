import React, { useState } from 'react';

export default function Checkpoint({ question, onAnswer, questionIndex }) {
  const [inputValue, setInputValue] = useState('');
  const [feedbackState, setFeedbackState] = useState(null);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    if (submitted || inputValue.trim() === '') return;
    setSubmitted(true);
    let isCorrect = false;

    if (question.isTextual) {
      const input = inputValue.trim().toLowerCase();
      const keyPhrases = ['只能向右', '只能向下', '一条路径', '唯一', '只有', '一直向右', '一直向下', '没有其他'];
      isCorrect = keyPhrases.some(phrase => input.includes(phrase)) || input.length >= 8;
    } else {
      isCorrect = parseInt(inputValue, 10) === question.answer;
    }

    setFeedbackState(isCorrect ? 'correct' : 'incorrect');
    onAnswer(isCorrect, inputValue);
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    if (!submitted) {
      setInputValue(typeof question.answer === 'number' ? String(question.answer) : question.answer);
    }
  };

  const handleShowHint = () => {
    setShowHint(true);
  };

  const inputClass = feedbackState === 'correct'
    ? 'input-field correct'
    : feedbackState === 'incorrect'
    ? 'input-field incorrect'
    : 'input-field';

  const icon = questionIndex === 0 ? '1️⃣' : questionIndex === 1 ? '2️⃣' : questionIndex === 2 ? '3️⃣' : '❓';

  return (
    <div className="card" style={{ borderLeft: '4px solid #7c3aed' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: '1.1rem' }}>{icon}</span>
        <span className="badge" style={{ background: '#ede9fe', color: '#7c3aed', borderColor: '#c4b5fd' }}>
          思考题 {questionIndex + 1}
        </span>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          检验你的理解
        </span>
      </div>
      
      <p style={{ fontSize: '0.9rem', lineHeight: 1.7, marginBottom: 20 }}>
        {question.question}
      </p>

      <div className="input-group" style={{ marginBottom: 16 }}>
        <label className="input-label" style={{ marginBottom: 8 }}>
          {question.isTextual ? '📝 你的解释：' : '🔢 你的答案（输入数字）：'}
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <input
            type={question.isTextual ? 'text' : 'number'}
            className={inputClass}
            value={inputValue}
            onChange={(e) => {
              if (!submitted) setInputValue(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !submitted) handleSubmit();
            }}
            placeholder={question.isTextual ? '请输入你的理解...' : '输入数值'}
            disabled={submitted}
            style={{ 
              flex: question.isTextual ? 1 : '0 1 auto',
              minWidth: question.isTextual ? 200 : 140,
              maxWidth: question.isTextual ? undefined : 200
            }}
          />
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitted || inputValue.trim() === ''}
            style={{ minWidth: 85 }}
          >
            ✓ 提交
          </button>
        </div>
      </div>

      {feedbackState === 'correct' && (
        <div className="feedback feedback-correct" style={{ marginTop: 12 }}>
          ✅ <strong>回答正确！</strong>{question.isTextual ? '你的理解非常到位。' : '你准确地预测了 DP 递推结果。'}
        </div>
      )}

      {feedbackState === 'incorrect' && (
        <div className="feedback feedback-incorrect" style={{ marginTop: 12 }}>
          ❌ <strong>回答不正确。</strong>别灰心，查看下面的提示或参考答案，理解后再试一次。
        </div>
      )}

      <div className="btn-group" style={{ marginTop: 16 }}>
        <button
          className="btn btn-outline btn-sm"
          onClick={handleShowHint}
          disabled={showHint}
          style={{ minWidth: 100 }}
        >
          💡 显示提示
        </button>
        <button
          className="btn btn-warning btn-sm"
          onClick={handleShowAnswer}
          disabled={showAnswer}
          style={{ minWidth: 100 }}
        >
          🔍 显示答案
        </button>
      </div>

      {showHint && (
        <div className="hint-text" style={{ marginTop: 12 }}>
          <strong>💡 提示：</strong> {question.hint}
        </div>
      )}

      {showAnswer && (
        <div className="feedback feedback-info" style={{ marginTop: 12 }}>
          <strong>📖 参考答案：</strong>
          {typeof question.answer === 'number' 
            ? <span style={{ fontFamily: 'SF Mono, Fira Code, monospace', fontWeight: 700, fontSize: '1.05rem' }}> {question.answer}</span>
            : <span> {question.answer}</span>
          }
        </div>
      )}
    </div>
  );
}