import React, { useState } from 'react';

function NumericCheckpoint({ checkpoint, onLog }) {
  const [input, setInput] = useState('');
  const [feedback, setFeedback] = useState(null); // 'correct' | 'incorrect' | null
  const [hintLevel, setHintLevel] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [attempts, setAttempts] = useState(0);

  const handleSubmit = (e) => {
    e.preventDefault();
    const parsed = parseInt(input, 10);
    if (isNaN(parsed)) return;

    setAttempts((a) => a + 1);

    if (parsed === checkpoint.answer) {
      setFeedback('correct');
      onLog(`Checkpoint ${checkpoint.id}: Correct answer (${checkpoint.answer}).`);
    } else {
      setFeedback('incorrect');
      onLog(`Checkpoint ${checkpoint.id}: Incorrect attempt — answered ${parsed}.`);
    }
  };

  const handleHint = () => {
    const nextLevel = hintLevel + 1;
    if (nextLevel <= checkpoint.hints.length) {
      setHintLevel(nextLevel);
      onLog(`Checkpoint ${checkpoint.id}: Hint ${nextLevel} revealed.`);
    }
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    setFeedback(null);
    onLog(`Checkpoint ${checkpoint.id}: Answer revealed (${checkpoint.answerDisplay}).`);
  };

  const handleReset = () => {
    setInput('');
    setFeedback(null);
    setHintLevel(0);
    setShowAnswer(false);
    setAttempts(0);
  };

  return (
    <div className="checkpoint-card">
      <h4 className="checkpoint-title">Checkpoint {checkpoint.id}</h4>
      <p className="checkpoint-question">{checkpoint.question}</p>

      <form onSubmit={handleSubmit} className="checkpoint-form">
        <input
          type="number"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter your answer..."
          disabled={feedback === 'correct' || showAnswer}
          className="checkpoint-input"
          aria-label={`Answer for checkpoint ${checkpoint.id}`}
        />
        <button
          type="submit"
          disabled={feedback === 'correct' || showAnswer || input === ''}
          className="btn btn-primary"
        >
          Submit
        </button>
      </form>

      {feedback === 'correct' && (
        <div className="feedback feedback--correct" role="alert">
          <strong>Correct!</strong> {checkpoint.explanation || `The answer is ${checkpoint.answerDisplay}.`}
        </div>
      )}
      {feedback === 'incorrect' && (
        <div className="feedback feedback--incorrect" role="alert">
          <strong>Not quite.</strong> Try again or use a hint.
        </div>
      )}
      {showAnswer && (
        <div className="feedback feedback--reveal" role="alert">
          <strong>Answer:</strong> {checkpoint.answerDisplay}
          {checkpoint.explanation && <p>{checkpoint.explanation}</p>}
        </div>
      )}

      {hintLevel > 0 && (
        <div className="hints-box">
          {checkpoint.hints.slice(0, hintLevel).map((hint, idx) => (
            <p key={idx} className="hint-text">
              <span className="hint-label">Hint {idx + 1}:</span> {hint}
            </p>
          ))}
        </div>
      )}

      <div className="checkpoint-actions">
        {feedback !== 'correct' && !showAnswer && hintLevel < checkpoint.hints.length && (
          <button onClick={handleHint} className="btn btn-hint">
            Hint
          </button>
        )}
        {feedback !== 'correct' && !showAnswer && (
          <button onClick={handleShowAnswer} className="btn btn-reveal">
            Show Answer
          </button>
        )}
        {(feedback === 'correct' || showAnswer || attempts > 0) && (
          <button onClick={handleReset} className="btn btn-reset">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

function McqCheckpoint({ checkpoint, onLog }) {
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);

  const handleSelect = (idx) => {
    if (feedback === 'correct' || showAnswer) return;
    setSelected(idx);
    if (idx === checkpoint.answer) {
      setFeedback('correct');
      onLog(`Checkpoint ${checkpoint.id}: Correct — selected option ${String.fromCharCode(65 + idx)}.`);
    } else {
      setFeedback('incorrect');
      onLog(`Checkpoint ${checkpoint.id}: Incorrect — selected option ${String.fromCharCode(65 + idx)}.`);
    }
  };

  const handleHint = () => {
    const next = hintLevel + 1;
    if (next <= checkpoint.hints.length) {
      setHintLevel(next);
      onLog(`Checkpoint ${checkpoint.id}: Hint ${next} revealed.`);
    }
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    setFeedback(null);
    onLog(`Checkpoint ${checkpoint.id}: Answer revealed (${checkpoint.answerDisplay}).`);
  };

  const handleReset = () => {
    setSelected(null);
    setFeedback(null);
    setHintLevel(0);
    setShowAnswer(false);
  };

  return (
    <div className="checkpoint-card">
      <h4 className="checkpoint-title">Checkpoint {checkpoint.id}</h4>
      <p className="checkpoint-question">{checkpoint.question}</p>

      <div className="mcq-options">
        {checkpoint.options.map((opt, idx) => {
          let optClass = 'mcq-option';
          if (selected === idx) optClass += ' mcq-option--selected';
          if (feedback && idx === checkpoint.answer) optClass += ' mcq-option--correct';
          if (feedback === 'incorrect' && selected === idx && idx !== checkpoint.answer)
            optClass += ' mcq-option--wrong';
          if (showAnswer && idx === checkpoint.answer) optClass += ' mcq-option--correct';

          return (
            <button
              key={idx}
              className={optClass}
              onClick={() => handleSelect(idx)}
              disabled={feedback === 'correct' || showAnswer}
              aria-label={`Option ${String.fromCharCode(65 + idx)}`}
            >
              <span className="mcq-letter">{String.fromCharCode(65 + idx)}</span>
              <span className="mcq-text">{opt}</span>
            </button>
          );
        })}
      </div>

      {feedback === 'correct' && (
        <div className="feedback feedback--correct" role="alert">
          <strong>Correct!</strong> Well reasoned.
        </div>
      )}
      {feedback === 'incorrect' && (
        <div className="feedback feedback--incorrect" role="alert">
          <strong>Not quite.</strong> Think about the movement rules and try again.
        </div>
      )}
      {showAnswer && (
        <div className="feedback feedback--reveal" role="alert">
          <strong>Answer:</strong> {checkpoint.answerDisplay}
        </div>
      )}

      {hintLevel > 0 && (
        <div className="hints-box">
          {checkpoint.hints.slice(0, hintLevel).map((hint, idx) => (
            <p key={idx} className="hint-text">
              <span className="hint-label">Hint {idx + 1}:</span> {hint}
            </p>
          ))}
        </div>
      )}

      <div className="checkpoint-actions">
        {feedback !== 'correct' && !showAnswer && hintLevel < checkpoint.hints.length && (
          <button onClick={handleHint} className="btn btn-hint">
            Hint
          </button>
        )}
        {feedback !== 'correct' && !showAnswer && (
          <button onClick={handleShowAnswer} className="btn btn-reveal">
            Show Answer
          </button>
        )}
        {(feedback === 'correct' || showAnswer || selected !== null) && (
          <button onClick={handleReset} className="btn btn-reset">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export default function CheckpointPanel({ checkpoints, onLog }) {
  return (
    <div className="checkpoint-panel">
      <h3 className="section-title">Check Your Understanding</h3>
      {checkpoints.map((cp) =>
        cp.type === 'numeric' ? (
          <NumericCheckpoint key={cp.id} checkpoint={cp} onLog={onLog} />
        ) : (
          <McqCheckpoint key={cp.id} checkpoint={cp} onLog={onLog} />
        )
      )}
    </div>
  );
}
