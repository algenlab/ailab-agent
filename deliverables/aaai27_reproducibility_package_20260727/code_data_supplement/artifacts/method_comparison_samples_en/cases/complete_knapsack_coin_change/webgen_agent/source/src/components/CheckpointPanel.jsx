import React, { useState } from 'react';

export default function CheckpointPanel({
  checkpoint,
  onAnswer,
  onHint,
  onShowAnswer,
  answered,
  answerResult,
  hintVisible,
  showAnswerVisible
}) {
  const [selectedOption, setSelectedOption] = useState(null);

  if (!checkpoint) return null;

  const handleSubmit = () => {
    if (selectedOption !== null && !answered) {
      onAnswer(checkpoint.id, selectedOption);
    }
  };

  const isCorrect = answerResult === 'correct';
  const isIncorrect = answerResult === 'incorrect';

  return (
    <div className={`checkpoint-panel ${isCorrect ? 'checkpoint-correct' : ''} ${isIncorrect ? 'checkpoint-incorrect' : ''}`}>
      <h3 className="checkpoint-title">{checkpoint.title}</h3>
      <p className="checkpoint-question">{checkpoint.question}</p>

      <div className="checkpoint-options">
        {checkpoint.options.map((opt, idx) => {
          let optClass = 'checkpoint-option';
          if (answered && idx === checkpoint.correctIndex) optClass += ' option-correct-reveal';
          if (answered && idx === selectedOption && idx !== checkpoint.correctIndex) optClass += ' option-incorrect-reveal';
          if (!answered && idx === selectedOption) optClass += ' option-selected';

          return (
            <label key={idx} className={optClass}>
              <input
                type="radio"
                name={`checkpoint-${checkpoint.id}`}
                value={idx}
                checked={selectedOption === idx}
                onChange={() => !answered && setSelectedOption(idx)}
                disabled={answered}
              />
              <span className="option-text">{opt}</span>
            </label>
          );
        })}
      </div>

      <div className="checkpoint-actions">
        {!answered && (
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={selectedOption === null}
          >
            Submit Answer
          </button>
        )}
        {!answered && !hintVisible && (
          <button className="btn btn-hint" onClick={() => onHint(checkpoint.id)}>
            💡 Hint
          </button>
        )}
        {!answered && !showAnswerVisible && (
          <button className="btn btn-reveal" onClick={() => onShowAnswer(checkpoint.id)}>
            👁 Show Answer
          </button>
        )}
      </div>

      {hintVisible && checkpoint.hint && (
        <div className="feedback hint-feedback">
          <strong>Hint:</strong> {checkpoint.hint}
        </div>
      )}

      {showAnswerVisible && (
        <div className="feedback reveal-feedback">
          <strong>Answer:</strong> Option {(checkpoint.correctIndex + 1)} — {checkpoint.options[checkpoint.correctIndex]}
          <br />
          <strong>Explanation:</strong> {checkpoint.explanation}
        </div>
      )}

      {isCorrect && (
        <div className="feedback correct-feedback">
          ✅ <strong>Correct!</strong> {checkpoint.explanation}
        </div>
      )}

      {isIncorrect && (
        <div className="feedback incorrect-feedback">
          ❌ <strong>Not quite.</strong> The correct answer is option {(checkpoint.correctIndex + 1)}: "{checkpoint.options[checkpoint.correctIndex]}".
          <br />
          {checkpoint.explanation}
        </div>
      )}
    </div>
  );
}
