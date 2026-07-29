import React, { useState } from 'react';
import { checkpointQuestion } from '../data/checkpointData';

export default function Checkpoint({ onLog }) {
  const [selected, setSelected] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  const isCorrect = submitted && selected === checkpointQuestion.correctOptionId;

  const handleSubmit = () => {
    if (!selected) return;
    setSubmitted(true);
    onLog({
      type: 'checkpoint',
      action: `Answered checkpoint: ${isCorrect ? 'correct' : 'incorrect'}. Selected ${selected.toUpperCase()}.`
    });
  };

  const handleHint = () => {
    setShowHint(true);
    onLog({ type: 'hint', action: 'Hint requested for checkpoint.' });
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    setSubmitted(true);
    setSelected(checkpointQuestion.correctOptionId);
    onLog({ type: 'showAnswer', action: 'Show answer used for checkpoint.' });
  };

  const resetCheckpoint = () => {
    setSelected(null);
    setSubmitted(false);
    setShowHint(false);
    setShowAnswer(false);
  };

  return (
    <div className="checkpoint card">
      <h2>Checkpoint</h2>
      <p className="question">
        <strong>{checkpointQuestion.title}:</strong><br />
        Current heap: {JSON.stringify(checkpointQuestion.scenario.heapBefore)}, k = {checkpointQuestion.scenario.k}, next element = {checkpointQuestion.scenario.nextElement}.<br />
        After pushing {checkpointQuestion.scenario.nextElement}, what will the heap become? What is the top?
      </p>

      <div className="options">
        {checkpointQuestion.options.map((opt) => (
          <label key={opt.id} className={`option ${submitted && opt.id === checkpointQuestion.correctOptionId ? 'correct' : ''} ${submitted && selected === opt.id && opt.id !== checkpointQuestion.correctOptionId ? 'incorrect' : ''}`}>
            <input
              type="radio"
              name="checkpoint"
              value={opt.id}
              checked={selected === opt.id}
              onChange={() => !submitted && setSelected(opt.id)}
              disabled={submitted}
            />
            <span>{opt.text}</span>
          </label>
        ))}
      </div>

      <div className="actions">
        <button onClick={handleSubmit} disabled={!selected || submitted} className="btn btn-primary">Submit</button>
        <button onClick={handleHint} className="btn">Hint</button>
        <button onClick={handleShowAnswer} className="btn btn-secondary">Show Answer</button>
      </div>

      {showHint && !showAnswer && (
        <div className="feedback hint">
          <p><strong>Hint:</strong> {checkpointQuestion.hint}</p>
        </div>
      )}

      {submitted && (
        <div className={`feedback ${isCorrect ? 'correct-feedback' : 'incorrect-feedback'}`}>
          {isCorrect ? (
            <p>✅ Correct! {checkpointQuestion.explanation}</p>
          ) : (
            <p>❌ Incorrect. {checkpointQuestion.explanation}</p>
          )}
        </div>
      )}

      {submitted && (
        <button onClick={resetCheckpoint} className="btn btn-link">Try again</button>
      )}
    </div>
  );
}
  