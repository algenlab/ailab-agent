import React, { useState } from 'react';
import './InputDisplay.css';

export default function InputDisplay({ nums, target, answer, showAnswer, onGuess, addLog }) {
  const [guessValue, setGuessValue] = useState('');
  const [guessResult, setGuessResult] = useState(null);

  const handleGuessSubmit = () => {
    const parsed = parseInt(guessValue);
    if (isNaN(parsed)) {
      setGuessResult({ correct: false, message: '请输入有效的整数' });
      return;
    }
    const isCorrect = parsed === answer;
    setGuessResult({
      correct: isCorrect,
      message: isCorrect
        ? `✅ 完全正确！答案就是 ${answer}。`
        : `❌ 不对。你猜的是 ${parsed}，正确答案是 ${answer}。`
    });
    if (onGuess) onGuess(isCorrect);
    if (addLog) addLog(
      isCorrect ? 'correct' : 'incorrect',
      `猜测答案: ${parsed} — ${isCorrect ? '正确！' : '不正确'}`
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleGuessSubmit();
  };

  return (
    <div className="input-display">
      <h3 className="section-title">📋 输入数据</h3>
      <div className="input-row">
        <div className="input-field nums-field">
          <span className="input-label">nums</span>
          <div className="array-display">
            {nums.map((num, i) => (
              <span key={i} className="array-element">
                <span className="array-index">{i}</span>
                <span className="array-value">{num}</span>
              </span>
            ))}
          </div>
        </div>
        <div className="input-field target-field">
          <span className="input-label">target</span>
          <span className="target-value">{target}</span>
        </div>
      </div>

      <div className="answer-section">
        <div className="answer-column">
          <span className="input-label">预期答案</span>
          {showAnswer ? (
            <span className="answer-value revealed">{answer}</span>
          ) : (
            <span className="answer-value hidden">???</span>
          )}
        </div>

        <div className="answer-column guess-column">
          <span className="input-label">你的猜测</span>
          <div className="guess-input-row">
            <input
              type="text"
              className="guess-input"
              placeholder="输入答案..."
              value={guessValue}
              onChange={(e) => {
                setGuessValue(e.target.value);
                setGuessResult(null);
              }}
              onKeyDown={handleKeyDown}
              disabled={showAnswer}
            />
            <button
              className="btn btn-guess"
              onClick={handleGuessSubmit}
              disabled={showAnswer || guessValue.trim() === ''}
            >
              验证
            </button>
          </div>
          {guessResult && (
            <span className={`guess-feedback ${guessResult.correct ? 'guess-correct' : 'guess-incorrect'}`}>
              {guessResult.message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
