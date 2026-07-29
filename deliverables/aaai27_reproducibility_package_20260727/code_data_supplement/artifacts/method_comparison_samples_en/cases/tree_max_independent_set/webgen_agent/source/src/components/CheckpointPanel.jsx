import React from 'react';

export default function CheckpointPanel({
  checkpoint,
  state,
  onAnswerChange,
  onSubmit,
  onShowHint,
  onShowAnswer
}) {
  const { answers = {}, submitted = false, correct = null, showAnswer = false, showHint = false } = state;

  let feedback = null;
  if (submitted) {
    if (correct) {
      feedback = <div className="feedback-text correct">✓ Correct! {checkpoint.explanation}</div>;
    } else {
      feedback = <div className="feedback-text incorrect">✗ Incorrect. Try again or use hint / show answer.</div>;
    }
  }

  const displayValues = showAnswer ? checkpoint.correctValues : answers;

  return (
    <div className="checkpoint-panel">
      <h3>💡 Checkpoint</h3>
      <p className="question-text">{checkpoint.question}</p>

      <div className="checkpoint-inputs">
        {checkpoint.inputFields.map(field => (
          <label key={field.key}>
            {field.label}
            <input
              type={field.type}
              value={displayValues[field.key] !== undefined ? displayValues[field.key] : ''}
              onChange={(e) => onAnswerChange(field.key, e.target.value)}
              disabled={submitted && correct}
              aria-label={field.label}
            />
          </label>
        ))}
      </div>

      <div className="checkpoint-actions">
        <button className="primary" onClick={onSubmit} disabled={submitted && correct} aria-label="Submit answer">
          Submit
        </button>
        <button onClick={onShowHint} aria-label="Show hint">
          💡 Hint
        </button>
        <button onClick={onShowAnswer} aria-label="Show answer">
          👁 Show Answer
        </button>
      </div>

      {showHint && (
        <div className="feedback-text" style={{ color: '#92400e', marginTop: 8 }}>
          {checkpoint.hint}
        </div>
      )}

      {feedback}
    </div>
  );
}