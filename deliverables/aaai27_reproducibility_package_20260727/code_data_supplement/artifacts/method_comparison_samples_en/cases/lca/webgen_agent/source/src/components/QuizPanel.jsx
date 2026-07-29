import React from 'react';

/**
 * QuizPanel — renders checkpoint quiz questions with interactive options.
 *
 * Props:
 *   questions        : array of question objects
 *   quizState        : map of questionId -> { answered, selectedIndex, isCorrect, hintShown, revealed }
 *   onSelectOption   : (questionId, optionIndex) => void
 *   onSubmitAnswer   : (questionId) => void
 *   onShowHint       : (questionId) => void
 *   onRevealAnswer   : (questionId) => void
 */
export default function QuizPanel({
  questions,
  quizState,
  onSelectOption,
  onSubmitAnswer,
  onShowHint,
  onRevealAnswer,
}) {
  return (
    <div className="quiz-panel" role="region" aria-label="Checkpoint quiz questions">
      {questions.map((q) => {
        const state = quizState[q.id] || {
          answered: false,
          selectedIndex: null,
          isCorrect: false,
          hintShown: false,
          revealed: false,
        };

        const showFeedback = state.answered || state.revealed;
        const allDisabled = state.answered && state.isCorrect;

        function getOptionClass(idx) {
          if (state.revealed && idx === q.correctIndex) return 'correct';
          if (state.answered && state.isCorrect && idx === state.selectedIndex) return 'correct';
          if (state.answered && !state.isCorrect && idx === state.selectedIndex) return 'incorrect';
          if (state.answered && !state.isCorrect && idx === q.correctIndex) return 'correct';
          if (idx === state.selectedIndex && !state.answered) return 'selected';
          return '';
        }

        return (
          <div
            key={q.id}
            className={`quiz-item${showFeedback ? (state.isCorrect || state.revealed ? ' answered-correct' : ' answered-incorrect') : ''}`}
          >
            <div className="quiz-scenario">{q.scenario}</div>
            <div className="quiz-question">
              Q{q.id + 1}. {q.question}
            </div>

            <div className="quiz-options" role="radiogroup" aria-label={`Options for question ${q.id + 1}`}>
              {q.options.map((opt, idx) => (
                <button
                  key={idx}
                  className={`quiz-option ${getOptionClass(idx)}`}
                  onClick={() => {
                    if (allDisabled) return;
                    onSelectOption(q.id, idx);
                  }}
                  disabled={allDisabled}
                  aria-label={`Option: ${opt}`}
                >
                  {opt}
                </button>
              ))}
            </div>

            <div className="quiz-actions">
              {!state.answered && state.selectedIndex !== null && (
                <button
                  className="btn btn-primary"
                  onClick={() => onSubmitAnswer(q.id)}
                  aria-label="Submit answer"
                >
                  Check Answer
                </button>
              )}
              {!state.hintShown && !state.revealed && !allDisabled && (
                <button
                  className="btn btn-secondary"
                  onClick={() => onShowHint(q.id)}
                  aria-label="Show hint"
                >
                  💡 Hint
                </button>
              )}
              {!state.revealed && !allDisabled && (
                <button
                  className="btn btn-secondary"
                  onClick={() => onRevealAnswer(q.id)}
                  aria-label="Reveal answer"
                >
                  👁 Reveal Answer
                </button>
              )}
            </div>

            {state.hintShown && !state.revealed && !allDisabled && (
              <div className="quiz-hint" role="status">
                <strong>Hint:</strong> {q.hint}
              </div>
            )}

            {state.revealed && (
              <div className="quiz-feedback correct" role="status">
                <strong>Answer:</strong> {q.options[q.correctIndex]}
                <br />
                {q.explanation}
              </div>
            )}

            {state.answered && !state.revealed && (
              <div className={`quiz-feedback ${state.isCorrect ? 'correct' : 'incorrect'}`} role="status">
                {state.isCorrect ? (
                  <>
                    <strong>✓ Correct!</strong> {q.explanation}
                  </>
                ) : (
                  <>
                    <strong>✗ Incorrect.</strong> You selected "{q.options[state.selectedIndex]}". Try again or use a hint!
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
