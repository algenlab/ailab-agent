import React, { useState } from 'react';
import type { CheckpointQuestion } from '../data/questions';
import InfoTooltip from './InfoTooltip';

interface CheckpointPanelProps {
  question: CheckpointQuestion;
  onCorrect: (questionId: number) => void;
  onIncorrect: (questionId: number) => void;
  onHint: (questionId: number) => void;
  onShowAnswer: (questionId: number, answer: string) => void;
}

const CheckpointPanel: React.FC<CheckpointPanelProps> = ({
  question,
  onCorrect,
  onIncorrect,
  onHint,
  onShowAnswer,
}) => {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const [questionKey, setQuestionKey] = useState(0);

  // Reset state when question changes (compare by id)
  const qFingerprint = `${question.id}`;
  React.useEffect(() => {
    setSelectedIndex(null);
    setSubmitted(false);
    setIsCorrect(null);
    setHintVisible(false);
    setAnswerRevealed(false);
    setQuestionKey((k) => k + 1);
  }, [qFingerprint]);

  const handleSubmit = () => {
    if (selectedIndex === null) return;
    setSubmitted(true);
    const correct = selectedIndex === question.correctIndex;
    setIsCorrect(correct);
    if (correct) {
      onCorrect(question.id);
    } else {
      onIncorrect(question.id);
    }
  };

  const handleHint = () => {
    setHintVisible(true);
    onHint(question.id);
  };

  const handleShowAnswer = () => {
    setAnswerRevealed(true);
    setSubmitted(true);
    setIsCorrect(null);
    setSelectedIndex(question.correctIndex);
    onShowAnswer(question.id, question.options[question.correctIndex]);
  };

  const handleRetry = () => {
    setSelectedIndex(null);
    setSubmitted(false);
    setIsCorrect(null);
    setHintVisible(false);
    setAnswerRevealed(false);
  };

  return (
    <div style={styles.container} key={questionKey}>
      <div style={styles.headerRow}>
        <h3 style={styles.title}>
          Checkpoint Question {question.id}
          <InfoTooltip text="Answer this question to test your understanding. Your response will be recorded in the activity log." />
        </h3>
        {submitted && isCorrect === true && (
          <span style={styles.correctBadge}>✓ Correct</span>
        )}
        {submitted && isCorrect === false && (
          <span style={styles.incorrectBadge}>✗ Incorrect</span>
        )}
        {answerRevealed && (
          <span style={styles.revealedBadge}>Answer revealed</span>
        )}
      </div>

      <p style={styles.questionText}>{question.question}</p>

      <div style={styles.options}>
        {question.options.map((opt, idx) => {
          let optStyle: React.CSSProperties = { ...styles.option };
          const isSelected = selectedIndex === idx;

          if (submitted || answerRevealed) {
            if (idx === question.correctIndex) {
              optStyle = { ...optStyle, ...styles.optionCorrect };
            } else if (isSelected && !isCorrect) {
              optStyle = { ...optStyle, ...styles.optionIncorrect };
            }
          } else if (isSelected) {
            optStyle = { ...optStyle, ...styles.optionSelected };
          }

          return (
            <label
              key={idx}
              style={optStyle}
              aria-label={`Option ${String.fromCharCode(65 + idx)}: ${opt}`}
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                value={idx}
                checked={isSelected}
                onChange={() => {
                  if (!submitted && !answerRevealed) {
                    setSelectedIndex(idx);
                  }
                }}
                disabled={submitted || answerRevealed}
                style={styles.radio}
              />
              <span style={styles.optionLetter}>
                {String.fromCharCode(65 + idx)}.
              </span>
              <span style={styles.optionText}>{opt}</span>
            </label>
          );
        })}
      </div>

      {/* Feedback area */}
      {submitted && isCorrect === true && (
        <div style={styles.feedbackCorrect}>
          <strong>Correct!</strong> {question.explanation}
        </div>
      )}
      {submitted && isCorrect === false && (
        <div style={styles.feedbackIncorrect}>
          <strong>Not quite.</strong> {question.explanation}
        </div>
      )}
      {hintVisible && (
        <div style={styles.hintBox}>
          <strong>Hint:</strong> Think about what happens when two nodes have different roots in Union-Find. Look at the parent array and trace the find operation.
        </div>
      )}
      {answerRevealed && (
        <div style={styles.answerRevealedBox}>
          <strong>Answer:</strong> {question.options[question.correctIndex]}
        </div>
      )}

      <div style={styles.actions}>
        {!submitted && !answerRevealed && (
          <button
            style={styles.submitBtn}
            onClick={handleSubmit}
            disabled={selectedIndex === null}
          >
            Submit Answer
          </button>
        )}
        {(submitted && isCorrect === false) && (
          <button style={styles.retryBtn} onClick={handleRetry}>
            Try Again
          </button>
        )}
        {!answerRevealed && (
          <button style={styles.hintBtn} onClick={handleHint}>
            Show Hint
          </button>
        )}
        {!answerRevealed && (
          <button style={styles.showAnswerBtn} onClick={handleShowAnswer}>
            Show Answer
          </button>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '1.25rem',
    boxShadow: 'var(--shadow)',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  title: {
    fontSize: '1rem',
    fontWeight: 700,
    color: 'var(--text)',
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
  },
  correctBadge: {
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: 'var(--success-light)',
    color: 'var(--success)',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  incorrectBadge: {
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: 'var(--error-light)',
    color: 'var(--error)',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  revealedBadge: {
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    background: '#faf5ff',
    color: '#805ad5',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  questionText: {
    fontSize: '0.925rem',
    lineHeight: 1.6,
    color: 'var(--text)',
    marginBottom: '1rem',
    fontWeight: 500,
  },
  options: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    marginBottom: '1rem',
  },
  option: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.5rem',
    padding: '0.625rem 0.75rem',
    borderRadius: 'var(--radius-sm)',
    border: '2px solid var(--border)',
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
    background: '#fff',
  },
  optionSelected: {
    borderColor: 'var(--primary)',
    background: '#ebf8ff',
  },
  optionCorrect: {
    borderColor: 'var(--success)',
    background: 'var(--success-light)',
  },
  optionIncorrect: {
    borderColor: 'var(--error)',
    background: 'var(--error-light)',
  },
  radio: {
    marginTop: '2px',
    accentColor: 'var(--primary)',
  },
  optionLetter: {
    fontWeight: 700,
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
    minWidth: '1.25rem',
  },
  optionText: {
    fontSize: '0.875rem',
    color: 'var(--text)',
    lineHeight: 1.5,
  },
  feedbackCorrect: {
    padding: '0.75rem 1rem',
    background: 'var(--success-light)',
    border: '1px solid #9ae6b4',
    borderRadius: 'var(--radius-sm)',
    fontSize: '0.85rem',
    color: 'var(--success)',
    marginBottom: '0.75rem',
    lineHeight: 1.5,
  },
  feedbackIncorrect: {
    padding: '0.75rem 1rem',
    background: 'var(--error-light)',
    border: '1px solid #feb2b2',
    borderRadius: 'var(--radius-sm)',
    fontSize: '0.85rem',
    color: 'var(--error)',
    marginBottom: '0.75rem',
    lineHeight: 1.5,
  },
  hintBox: {
    padding: '0.75rem 1rem',
    background: 'var(--warning-light)',
    border: '1px solid #faf089',
    borderRadius: 'var(--radius-sm)',
    fontSize: '0.85rem',
    color: '#975a16',
    marginBottom: '0.75rem',
    lineHeight: 1.5,
  },
  answerRevealedBox: {
    padding: '0.75rem 1rem',
    background: '#faf5ff',
    border: '1px solid #e9d8fd',
    borderRadius: 'var(--radius-sm)',
    fontSize: '0.85rem',
    color: '#553c9a',
    marginBottom: '0.75rem',
    lineHeight: 1.5,
  },
  actions: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap',
  },
  submitBtn: {
    background: 'var(--primary)',
    color: '#fff',
    fontWeight: 600,
  },
  retryBtn: {
    background: '#ed8936',
    color: '#fff',
    fontWeight: 600,
  },
  hintBtn: {
    background: '#f7fafc',
    color: '#4a5568',
    border: '1px solid var(--border)',
  },
  showAnswerBtn: {
    background: '#faf5ff',
    color: '#805ad5',
    border: '1px solid #e9d8fd',
  },
};

export default CheckpointPanel;
