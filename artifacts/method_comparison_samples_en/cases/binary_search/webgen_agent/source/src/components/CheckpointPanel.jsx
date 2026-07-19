import React, { useState, useCallback } from 'react';

const QUESTIONS = [
  {
    id: 1,
    question: (
      <>
        Current search interval:{' '}
        <span className="inline-code">left=0</span>,{' '}
        <span className="inline-code">right=5</span>,{' '}
        <span className="inline-code">mid=2</span>,{' '}
        <span className="inline-code">nums=[-1,0,3,5,9,12]</span>,{' '}
        <span className="inline-code">target=9</span>.{' '}
        <span className="inline-code">
          nums[mid]=3 {'<'} target
        </span>
        . How will{' '}
        <span className="inline-code">left</span> and{' '}
        <span className="inline-code">right</span> update in the next step?
      </>
    ),
    options: [
      'left=3, right=5',
      'left=0, right=2',
      'left=2, right=5',
      'left=3, right=2',
    ],
    correctIndex: 0,
    explanation:
      'Since nums[mid]=3 < target=9, the target must be in the right half. We set left = mid + 1 = 3. The right pointer stays at 5. The new interval is [3, 5].',
    hint: 'When nums[mid] < target, we know the target cannot be at or to the left of mid. Which side do we keep?',
  },
  {
    id: 2,
    question: (
      <>
        At any step of binary search, which statement about the search interval and target always
        holds?
      </>
    ),
    options: [
      'A. target is definitely in the interval',
      'B. If target is in the array, it is always in the current interval',
      'C. The interval length is always even',
      'D. left is always less than right',
    ],
    correctIndex: 1,
    explanation:
      'The invariant of binary search is: if the target exists in the array, it remains within the current [left, right] interval. Option A is false because the target might not exist. Option C is false because intervals can be odd lengths. Option D is false because left can equal right.',
    hint: 'Think about what binary search guarantees (its invariant). What can we always say about the target relative to the current search interval?',
  },
  {
    id: 3,
    question: (
      <>
        Suppose <span className="inline-code">nums=[1,3,5,7,9]</span>,{' '}
        <span className="inline-code">target=4</span>. Modify the target value so that the search
        can stop early (i.e., fewer loop iterations than the original search). Provide the new
        target value.
      </>
    ),
    options: [
      'target=1',
      'target=5',
      'target=10',
      'target=6',
    ],
    correctIndex: 1,
    explanation:
      'With target=4, the algorithm would check mid=5 (index 2), then mid=3 (index 1), then mid=1 (index 0), making 3 comparisons before concluding the target is not found. If we set target=5, the very first mid value (index 2) matches the target, so the search stops after just 1 comparison (early stop).',
    hint: 'With target=4, the first midpoint is at index 2 with value 5. We then go left. Which target value would make the very first midpoint match?',
  },
  {
    id: 4,
    question: (
      <>
        A student says: "As long as nums is sorted, binary search can correctly return the index of
        any target, regardless of duplicates." Construct a counterexample using an array with
        duplicate elements to show this statement is wrong (assuming the requirement is to return
        the first occurrence position of target).
      </>
    ),
    options: [
      'nums=[1,2,2,2,3], target=2 — binary search may return index 2 instead of the first occurrence at index 1',
      'nums=[1,1,1,1,1], target=1 — binary search always returns index 0',
      'nums=[1,2,3,4,5], target=2 — binary search returns index 1',
      'nums=[1,2,2,3], target=3 — binary search correctly returns index 3',
    ],
    correctIndex: 0,
    explanation:
      'In nums=[1,2,2,2,3] with target=2, the standard binary search compares mid index 2 (value 2) and may return index 2 directly, even though the first occurrence is at index 1. Standard binary search does not guarantee returning the first occurrence when duplicates exist. You would need a modified binary search to find the first or last occurrence.',
    hint: 'Consider what happens when the midpoint itself is the target value but there are identical values to its left. Does standard binary search continue searching left?',
  },
];

export default function CheckpointPanel({ nums, target, addLogEntry }) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [completedQuestions, setCompletedQuestions] = useState(new Set());

  const q = QUESTIONS[currentQuestion];
  const isCorrect = submitted && selectedOption === q.correctIndex;
  const isIncorrect =
    submitted && selectedOption !== null && selectedOption !== q.correctIndex;

  const handleSelectOption = useCallback(
    (idx) => {
      if (submitted) return;
      setSelectedOption(idx);
      setShowHint(false);
      setShowAnswer(false);
    },
    [submitted],
  );

  const handleSubmit = useCallback(() => {
    if (selectedOption === null || submitted) return;

    setSubmitted(true);
    const correct = selectedOption === q.correctIndex;

    if (correct) {
      addLogEntry('correct', 'Question ' + q.id + ': Answered correctly');
      setCompletedQuestions((prev) => new Set([...prev, currentQuestion]));
    } else {
      addLogEntry(
        'incorrect',
        'Question ' +
          q.id +
          ': Answered incorrectly (chose option ' +
          (selectedOption + 1) +
          ')',
      );
    }
  }, [selectedOption, submitted, q, addLogEntry, currentQuestion]);

  const handleHint = useCallback(() => {
    setShowHint(true);
    setShowAnswer(false);
    addLogEntry('hint', 'Question ' + q.id + ': Requested hint');
  }, [q, addLogEntry]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    setShowHint(false);
    if (!submitted) {
      setSelectedOption(q.correctIndex);
      setSubmitted(true);
    }
    addLogEntry('reveal', 'Question ' + q.id + ': Revealed answer');
  }, [q, addLogEntry, submitted]);

  const handleRetry = useCallback(() => {
    setSelectedOption(null);
    setSubmitted(false);
    setShowHint(false);
    setShowAnswer(false);
    addLogEntry('step', 'Question ' + q.id + ': Retrying');
  }, [q, addLogEntry]);

  const handleNextQuestion = useCallback(() => {
    if (currentQuestion < QUESTIONS.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedOption(null);
      setSubmitted(false);
      setShowHint(false);
      setShowAnswer(false);
    }
  }, [currentQuestion]);

  const handlePrevQuestion = useCallback(() => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
      setSelectedOption(null);
      setSubmitted(false);
      setShowHint(false);
      setShowAnswer(false);
    }
  }, [currentQuestion]);

  return (
    <section className="section">
      <h2 className="section-title">
        <span className="icon" role="img" aria-label="quiz">
          ✅
        </span>
        Checkpoint: Test Your Understanding
      </h2>

      {/* Question navigation */}
      <div className="question-nav">
        {QUESTIONS.map((qst, idx) => (
          <button
            key={qst.id}
            className={
              'question-nav-btn' +
              (idx === currentQuestion ? ' active' : '') +
              (completedQuestions.has(idx) ? ' completed' : '')
            }
            onClick={() => {
              setCurrentQuestion(idx);
              setSelectedOption(null);
              setSubmitted(false);
              setShowHint(false);
              setShowAnswer(false);
            }}
          >
            Q{qst.id}
            {completedQuestions.has(idx) ? ' ✓' : ''}
          </button>
        ))}
      </div>

      {/* Question text */}
      <div className="checkpoint-question">
        <span className="question-number">Question {q.id}:</span> {q.question}
      </div>

      {/* Options */}
      <div className="checkpoint-options">
        {q.options.map((opt, idx) => {
          let optClass = 'option-btn';
          if (selectedOption === idx) optClass += ' selected';
          if (submitted && idx === q.correctIndex && !showAnswer)
            optClass += ' correct';
          if (isIncorrect && idx === selectedOption) optClass += ' incorrect';
          if (showAnswer && idx === q.correctIndex) optClass += ' correct';

          return (
            <button
              key={idx}
              className={optClass}
              onClick={() => handleSelectOption(idx)}
              disabled={submitted && !showAnswer}
              aria-label={'Option ' + (idx + 1) + ': ' + opt}
            >
              <strong>{String.fromCharCode(65 + idx)}.</strong> {opt}
            </button>
          );
        })}
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {!submitted && (
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={selectedOption === null}
          >
            Submit Answer
          </button>
        )}
        {submitted && !isCorrect && (
          <button className="btn" onClick={handleRetry}>
            ↻ Retry
          </button>
        )}
        <button
          className="btn"
          onClick={handleHint}
          disabled={showHint || showAnswer}
        >
          💡 Hint
        </button>
        <button
          className="btn"
          onClick={handleShowAnswer}
          disabled={showAnswer}
        >
          👁 Show Answer
        </button>
        <div style={{ flex: 1 }} />
        <button
          className="btn"
          onClick={handlePrevQuestion}
          disabled={currentQuestion === 0}
        >
          ← Prev Question
        </button>
        <button
          className="btn"
          onClick={handleNextQuestion}
          disabled={currentQuestion === QUESTIONS.length - 1}
        >
          Next Question →
        </button>
      </div>

      {/* Feedback */}
      {isCorrect && (
        <div className="feedback correct">
          <span>✓</span>
          <span>
            <strong>Correct!</strong> {q.explanation}
          </span>
        </div>
      )}
      {isIncorrect && (
        <div className="feedback incorrect">
          <span>✗</span>
          <span>
            <strong>Incorrect.</strong> The correct answer is option{' '}
            {String.fromCharCode(65 + q.correctIndex)}. {q.explanation}
          </span>
        </div>
      )}

      {/* Hint */}
      {showHint && !showAnswer && (
        <div className="hint-area">
          <strong>💡 Hint:</strong> {q.hint}
        </div>
      )}

      {/* Revealed answer */}
      {showAnswer && (
        <div className="answer-reveal">
          <strong>👁 Answer Revealed:</strong> The correct answer is option{' '}
          {String.fromCharCode(65 + q.correctIndex)}: "
          {q.options[q.correctIndex]}". {q.explanation}
        </div>
      )}
    </section>
  );
}
