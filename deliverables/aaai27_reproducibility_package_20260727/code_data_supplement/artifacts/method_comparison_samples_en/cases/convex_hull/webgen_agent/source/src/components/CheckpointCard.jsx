import React from 'react';

export default function CheckpointCard({ checkpoint, state, onAnswer, onShowHint, onRevealAnswer }) {
  const { answered, correct, selectedKey, hintVisible, answerRevealed } = state;

  let cardClass = 'checkpoint-card card';
  if (answered && correct) cardClass += ' answered-correct';
  if (answered && !correct) cardClass += ' answered-incorrect';

  return (
    <div className={cardClass}>
      <div className="checkpoint-title">{checkpoint.title}</div>
      <div className="checkpoint-question">{checkpoint.question}</div>

      <div className="checkpoint-options">
        {checkpoint.options.map((opt) => {
          let optClass = 'checkpoint-option';
          if (answered || answerRevealed) optClass += ' disabled';
          if (answered && selectedKey === opt.key) {
            optClass += correct ? ' selected-correct' : ' selected-incorrect';
          }
          if (answerRevealed && opt.key === checkpoint.correctKey) {
            optClass += ' revealed-correct';
          }
          return (
            <button
              key={opt.key}
              className={optClass}
              onClick={() => {
                if (!answered && !answerRevealed) onAnswer(checkpoint.id, opt.key);
              }}
              disabled={answered || answerRevealed}
              aria-label={`Option ${opt.key}: ${opt.text}`}
            >
              <span className="option-key">{opt.key}</span>
              <span>{opt.text}</span>
            </button>
          );
        })}
      </div>

      {answered && (
        <div className={`checkpoint-feedback ${correct ? 'correct' : 'incorrect'}`}>
          {correct
            ? '\u2705 Correct! ' + checkpoint.explanation
            : '\u274C Incorrect. The correct answer is ' + checkpoint.correctKey + '. ' + checkpoint.explanation}
        </div>
      )}

      {hintVisible && !answerRevealed && (
        <div className="checkpoint-hint">
          {'\uD83D\uDCA1 ' + checkpoint.hint}
        </div>
      )}

      <div className="checkpoint-actions">
        {!answered && !hintVisible && (
          <button className="checkpoint-action-btn hint-btn" onClick={() => onShowHint(checkpoint.id)}>
            {'\uD83D\uDCA1'} Show Hint
          </button>
        )}
        {!answerRevealed && (
          <button className="checkpoint-action-btn reveal-btn" onClick={() => onRevealAnswer(checkpoint.id)}>
            {'\uD83D\uDC41'} Reveal Answer
          </button>
        )}
      </div>
    </div>
  );
}