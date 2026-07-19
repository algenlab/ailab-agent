import React, { useState, useEffect, useRef } from 'react';

export default function CheckpointPanel({
  checkpoint,
  checkpointState,
  onSelectAnswer,
  onRevealHint,
  onRevealAnswer,
  onDismissFeedback
}) {
  const [selectedOption, setSelectedOption] = useState(
    checkpointState?.selectedOption ?? null
  );
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackType, setFeedbackType] = useState(null);
  const feedbackTimerRef = useRef(null);

  // Sync external state changes
  useEffect(() => {
    setSelectedOption(checkpointState?.selectedOption ?? null);
  }, [checkpointState?.selectedOption]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (feedbackTimerRef.current) {
        clearTimeout(feedbackTimerRef.current);
      }
    };
  }, []);

  if (!checkpoint) {
    return (
      <div className="checkpoint-panel checkpoint-empty">
        <p className="checkpoint-empty-text">No checkpoint for this step. Advance to see questions.</p>
      </div>
    );
  }

  const isAnswered = checkpointState?.answered || false;
  const isHintRevealed = checkpointState?.hintRevealed || false;
  const isAnswerRevealed = checkpointState?.answerRevealed || false;
  const wasCorrect = checkpointState?.isCorrect;

  const handleOptionClick = (index) => {
    if (isAnswered) return;
    setSelectedOption(index);
  };

  const handleSubmit = () => {
    if (selectedOption === null || isAnswered) return;
    const isCorrect = selectedOption === checkpoint.correctIndex;
    setFeedbackType(isCorrect ? 'correct' : 'incorrect');
    setShowFeedback(true);
    onSelectAnswer(checkpoint.id, selectedOption, isCorrect);
    // Clear any existing timer
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = null;
    }
  };

  const handleHint = () => {
    onRevealHint(checkpoint.id);
  };

  const handleShowAnswer = () => {
    onRevealAnswer(checkpoint.id);
    setSelectedOption(checkpoint.correctIndex);
    // Dismiss any lingering feedback when answer is revealed
    setShowFeedback(false);
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = null;
    }
  };

  const handleDismissFeedback = () => {
    setShowFeedback(false);
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = null;
    }
  };

  return (
    <div className="checkpoint-panel" role="region" aria-label={`Checkpoint: ${checkpoint.title}`}>
      <h3 className="checkpoint-title">{checkpoint.title}</h3>
      <p className="checkpoint-question">{checkpoint.question}</p>

      <div className="checkpoint-options" role="radiogroup" aria-label="Answer options">
        {checkpoint.options.map((option, index) => {
          let optionClass = 'checkpoint-option';
          if (isAnswerRevealed && index === checkpoint.correctIndex) {
            optionClass += ' option-revealed-correct';
          } else if (selectedOption === index) {
            optionClass += ' option-selected';
            if (isAnswered && index === checkpoint.correctIndex) {
              optionClass += ' option-correct';
            } else if (isAnswered && index !== checkpoint.correctIndex) {
              optionClass += ' option-incorrect';
            }
          } else if (isAnswered && index === checkpoint.correctIndex) {
            optionClass += ' option-correct';
          }

          return (
            <button
              key={`opt-${checkpoint.id}-${index}`}
              className={optionClass}
              onClick={() => handleOptionClick(index)}
              disabled={isAnswered}
              role="radio"
              aria-checked={selectedOption === index}
              aria-label={`Option ${String.fromCharCode(65 + index)}: ${option}`}
            >
              <span className="option-letter">{String.fromCharCode(65 + index)}</span>
              <span className="option-text">{option}</span>
              {isAnswered && index === checkpoint.correctIndex && (
                <span className="option-icon-correct" aria-label="Correct answer">✓</span>
              )}
              {isAnswered && selectedOption === index && index !== checkpoint.correctIndex && (
                <span className="option-icon-incorrect" aria-label="Incorrect answer">✗</span>
              )}
            </button>
          );
        })}
      </div>

      <div className="checkpoint-actions">
        {!isAnswered && selectedOption !== null && (
          <button className="btn btn-primary" onClick={handleSubmit}>
            Submit Answer
          </button>
        )}
        {!isHintRevealed && !isAnswerRevealed && (
          <button className="btn btn-hint" onClick={handleHint}>
            <span className="btn-icon" aria-hidden="true">💡</span> Hint
          </button>
        )}
        {!isAnswerRevealed && (
          <button className="btn btn-show-answer" onClick={handleShowAnswer}>
            <span className="btn-icon" aria-hidden="true">👁</span> Show Answer
          </button>
        )}
      </div>

      {/* Hint — always in DOM but visibility controlled */}
      <div
        className={`checkpoint-hint ${isHintRevealed && !isAnswerRevealed ? 'hint-visible' : ''}`}
        role="status"
        aria-hidden={!(isHintRevealed && !isAnswerRevealed)}
      >
        <strong>Hint:</strong> {checkpoint.hint}
      </div>

      {/* Explanation — always in DOM but visibility controlled */}
      <div
        className={`checkpoint-explanation ${isAnswerRevealed ? 'explanation-visible' : ''}`}
        role="status"
        aria-hidden={!isAnswerRevealed}
      >
        <strong>Answer:</strong> {checkpoint.explanation}
      </div>

      {/* Feedback — always in DOM but visibility controlled, no auto-dismiss */}
      <div
        className={`checkpoint-feedback feedback-${feedbackType || 'correct'} ${showFeedback ? 'feedback-visible' : ''}`}
        role="alert"
        aria-hidden={!showFeedback}
      >
        <p>
          <span className="feedback-icon" aria-hidden="true">
            {feedbackType === 'correct' ? '✓' : '✗'}
          </span>
          {feedbackType === 'correct'
            ? checkpoint.feedbackCorrect
            : checkpoint.feedbackIncorrect}
        </p>
        <button
          className="feedback-dismiss"
          onClick={handleDismissFeedback}
          aria-label="Dismiss feedback"
        >
          ×
        </button>
      </div>

      {/* Result — always in DOM but visibility controlled */}
      <div
        className={`checkpoint-result ${wasCorrect ? 'result-correct' : 'result-incorrect'} ${isAnswered && !showFeedback ? 'result-visible' : ''}`}
        role="status"
        aria-hidden={!(isAnswered && !showFeedback)}
      >
        {wasCorrect ? (
          <span><strong>✓ Correct!</strong> Well done.</span>
        ) : (
          <span><strong>✗ Incorrect.</strong> The correct answer has been highlighted above.</span>
        )}
      </div>
    </div>
  );
}