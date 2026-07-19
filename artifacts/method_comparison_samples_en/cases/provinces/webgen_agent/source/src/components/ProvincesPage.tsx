import React, { useState, useMemo, useCallback } from 'react';
import { problemInput, expectedAnswer, allSteps } from '../data/problemData';
import { checkpointQuestions } from '../data/questions';
import { useActivityLog } from '../hooks/useActivityLog';
import MatrixDisplay from './MatrixDisplay';
import ParentArrayDisplay from './ParentArrayDisplay';
import StepNavigator from './StepNavigator';
import CheckpointPanel from './CheckpointPanel';
import ActivityLog from './ActivityLog';
import AnswerBadge from './AnswerBadge';

export const ProvincesPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [activeQuestionIdx, setActiveQuestionIdx] = useState(0);
  const { entries, addEntry } = useActivityLog();

  const steps = useMemo(() => allSteps, []);
  const totalSteps = steps.length;
  const step = steps[Math.min(currentStep, totalSteps - 1)];

  const activeQuestion = checkpointQuestions[activeQuestionIdx];

  // Determine changed index for parent array visualization
  const changedIndex = useMemo(() => {
    if (currentStep === 0) return -1;
    const prev = steps[currentStep - 1];
    const curr = steps[currentStep];
    for (let k = 0; k < curr.parent.length; k++) {
      if (prev.parent[k] !== curr.parent[k]) return k;
    }
    return -1;
  }, [currentStep, steps]);

  const handlePrev = useCallback(() => {
    if (currentStep > 0) {
      const newStep = currentStep - 1;
      setCurrentStep(newStep);
      addEntry(
        `Navigated to step ${newStep + 1} of ${totalSteps}.`,
        'navigation',
      );
    }
  }, [currentStep, totalSteps, addEntry]);

  const handleNext = useCallback(() => {
    if (currentStep < totalSteps - 1) {
      const newStep = currentStep + 1;
      setCurrentStep(newStep);
      addEntry(
        `Navigated to step ${newStep + 1} of ${totalSteps}.`,
        'navigation',
      );
    }
  }, [currentStep, totalSteps, addEntry]);

  const handleGoTo = useCallback(
    (stepIdx: number) => {
      setCurrentStep(stepIdx);
      addEntry(
        `Jumped to step ${stepIdx + 1} of ${totalSteps}.`,
        'navigation',
      );
    },
    [totalSteps, addEntry],
  );

  const handleCorrect = useCallback(
    (questionId: number) => {
      addEntry(
        `Checkpoint question ${questionId}: answered correctly. Great job!`,
        'correct',
      );
    },
    [addEntry],
  );

  const handleIncorrect = useCallback(
    (questionId: number) => {
      addEntry(
        `Checkpoint question ${questionId}: answered incorrectly. Review the explanation and try again.`,
        'incorrect',
      );
    },
    [addEntry],
  );

  const handleHint = useCallback(
    (questionId: number) => {
      addEntry(
        `Checkpoint question ${questionId}: hint was requested.`,
        'hint',
      );
    },
    [addEntry],
  );

  const handleShowAnswer = useCallback(
    (questionId: number, answer: string) => {
      addEntry(
        `Checkpoint question ${questionId}: answer revealed \u2014 "${answer}".`,
        'answer',
      );
    },
    [addEntry],
  );

  const handleNextQuestion = useCallback(() => {
    if (activeQuestionIdx < checkpointQuestions.length - 1) {
      setActiveQuestionIdx((p) => p + 1);
      addEntry(
        `Moved to checkpoint question ${activeQuestionIdx + 2} of ${checkpointQuestions.length}.`,
        'navigation',
      );
    }
  }, [activeQuestionIdx, addEntry]);

  const handlePrevQuestion = useCallback(() => {
    if (activeQuestionIdx > 0) {
      setActiveQuestionIdx((p) => p - 1);
      addEntry(
        `Moved to checkpoint question ${activeQuestionIdx} of ${checkpointQuestions.length}.`,
        'navigation',
      );
    }
  }, [activeQuestionIdx, addEntry]);

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>Number of Provinces</h1>
        <div style={styles.subtitle}>
          <span style={styles.algoFamily}>Algorithm Family: Union Find</span>
        </div>
      </header>

      {/* Problem Statement */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Problem Statement</h2>
        <p style={styles.problemText}>
          In a large enterprise network, the physical connections between
          computers are represented by a symmetric matrix{' '}
          <code>isConnected</code>, where{' '}
          <code>isConnected[i][j] = 1</code> indicates that computers{' '}
          <em>i</em> and <em>j</em> are directly connected, and <code>0</code>{' '}
          indicates they are not. Diagonal elements are all <code>1</code> (each
          computer is connected to itself). If two computers can communicate
          through a series of direct connections, they belong to the same
          network area (called a “province”). Calculate the{' '}
          <strong>total number of distinct provinces</strong> in the entire
          network.
        </p>
      </section>

      {/* Input + Output */}
      <section style={styles.section}>
        <div style={styles.ioGrid}>
          <div style={styles.ioCard}>
            <MatrixDisplay
              matrix={problemInput.isConnected}
              label="Input: isConnected Matrix"
            />
          </div>
          <div style={styles.ioCardAnswer}>
            <AnswerBadge answer={expectedAnswer} />
            <p style={styles.answerNote}>
              The expected answer is <strong>2</strong> because computers 0 and
              1 form one province, and computer 2 forms a second province.
            </p>
          </div>
        </div>
      </section>

      {/* Reference Strategy */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Reference Strategy</h2>
        <p style={styles.problemText}>
          Use the <strong>Union-Find (Disjoint Set Union)</strong> algorithm.
          Initialize each computer as its own root (parent[i] = i). Iterate
          through all pairs (i, j) where{' '}
          {'j > i'}. If isConnected[i][j] = 1 and{' '}
          find(i) ≠ find(j), perform a union by setting parent[rootJ] =
          rootI. Finally, count the number of nodes where parent[i] = i to get
          the number of provinces. Path compression is applied during find
          operations for optimization.
        </p>
      </section>

      {/* Learning Objectives */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Learning Objectives</h2>
        <ul style={styles.objectiveList}>
          <li>
            Track the state changes of the parent array during the union-find
            merge process.
          </li>
          <li>
            Identify the optimization effect of path compression on the find
            operation in union-find.
          </li>
          <li>
            Predict the decreasing trend of the number of provinces by
            observing merge operations.
          </li>
        </ul>
      </section>

      {/* Step-by-Step Visualization */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Step-by-Step Visualization</h2>
        <StepNavigator
          currentStep={currentStep}
          totalSteps={totalSteps}
          onPrev={handlePrev}
          onNext={handleNext}
          onGoTo={handleGoTo}
          canGoPrev={currentStep > 0}
          canGoNext={currentStep < totalSteps - 1}
          description={step.description}
          provinceCount={step.provinceCount}
          i={step.i}
          j={step.j}
          unionPerformed={step.unionPerformed}
        />

        <div style={styles.vizGrid}>
          <div style={styles.vizCard}>
            <MatrixDisplay
              matrix={problemInput.isConnected}
              highlightI={step.i}
              highlightJ={step.j}
              label="isConnected Matrix"
            />
          </div>
          <div style={styles.vizCard}>
            <ParentArrayDisplay
              parent={step.parent}
              changedIndex={changedIndex}
              label={`Parent Array (after step ${currentStep + 1})`}
            />
            <div style={styles.parentLegend}>
              <span style={styles.legendItem}>
                <span
                  style={{ ...styles.legendDot, background: '#38a169' }}
                />{' '}
                Root node
              </span>
              <span style={styles.legendItem}>
                <span
                  style={{ ...styles.legendDot, background: '#ecc94b' }}
                />{' '}
                Changed
              </span>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div style={styles.progressBarWrapper}>
          <div
            style={{
              ...styles.progressFill,
              width: `${((currentStep + 1) / totalSteps) * 100}%`,
            }}
          />
        </div>
        <p style={styles.progressLabel}>
          {Math.round(((currentStep + 1) / totalSteps) * 100)}% complete
        </p>
      </section>

      {/* Checkpoint Questions */}
      <section style={styles.section}>
        <div style={styles.questionHeader}>
          <h2 style={styles.sectionTitle}>Checkpoint Questions</h2>
          <div style={styles.questionNav}>
            <button
              onClick={handlePrevQuestion}
              disabled={activeQuestionIdx === 0}
              style={styles.qNavBtn}
              aria-label="Previous question"
            >
              ← Prev
            </button>
            <span style={styles.qIndicator}>
              Question {activeQuestionIdx + 1} of {checkpointQuestions.length}
            </span>
            <button
              onClick={handleNextQuestion}
              disabled={
                activeQuestionIdx === checkpointQuestions.length - 1
              }
              style={styles.qNavBtn}
              aria-label="Next question"
            >
              Next →
            </button>
          </div>
        </div>
        <CheckpointPanel
          question={activeQuestion}
          onCorrect={handleCorrect}
          onIncorrect={handleIncorrect}
          onHint={handleHint}
          onShowAnswer={handleShowAnswer}
        />
      </section>

      {/* Activity Log */}
      <section style={styles.section}>
        <ActivityLog entries={entries} />
      </section>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: '1024px',
    margin: '0 auto',
    padding: '1.5rem 1rem 4rem',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '2rem',
    paddingTop: '1rem',
  },
  title: {
    fontSize: 'clamp(1.5rem, 3vw, 2.25rem)',
    fontWeight: 800,
    color: 'var(--text)',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    marginTop: '0.5rem',
  },
  algoFamily: {
    display: 'inline-block',
    padding: '0.25rem 0.75rem',
    borderRadius: '999px',
    background: '#ebf8ff',
    color: '#2b6cb0',
    fontSize: '0.85rem',
    fontWeight: 600,
  },
  section: {
    marginBottom: '2rem',
  },
  sectionTitle: {
    fontSize: '1.15rem',
    fontWeight: 700,
    marginBottom: '0.75rem',
    color: 'var(--text)',
    borderBottom: '2px solid var(--border)',
    paddingBottom: '0.5rem',
  },
  problemText: {
    fontSize: '0.925rem',
    lineHeight: 1.7,
    color: 'var(--text)',
  },
  ioGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1.5rem',
    alignItems: 'center',
  },
  ioCard: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '1.25rem',
    boxShadow: 'var(--shadow)',
    display: 'flex',
    justifyContent: 'center',
  },
  ioCardAnswer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '1rem',
    textAlign: 'center',
  },
  answerNote: {
    fontSize: '0.85rem',
    color: 'var(--text-muted)',
    lineHeight: 1.6,
    maxWidth: '320px',
  },
  objectiveList: {
    paddingLeft: '1.5rem',
    fontSize: '0.925rem',
    lineHeight: 1.8,
    color: 'var(--text)',
  },
  vizGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1.5rem',
    marginTop: '1.25rem',
  },
  vizCard: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '1.25rem',
    boxShadow: 'var(--shadow)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.75rem',
  },
  parentLegend: {
    display: 'flex',
    gap: '1rem',
    marginTop: '0.25rem',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.3rem',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  legendDot: {
    display: 'inline-block',
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  progressBarWrapper: {
    marginTop: '1.25rem',
    height: '8px',
    background: 'var(--border)',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #3182ce, #38a169)',
    borderRadius: '4px',
    transition: 'width 0.3s ease',
  },
  progressLabel: {
    textAlign: 'center' as const,
    fontSize: '0.75rem',
    color: 'var(--text-light)',
    marginTop: '0.375rem',
  },
  questionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
    marginBottom: '0.75rem',
  },
  questionNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  qNavBtn: {
    background: '#f7fafc',
    color: '#4a5568',
    border: '1px solid var(--border)',
    fontSize: '0.8rem',
    padding: '0.35rem 0.75rem',
  },
  qIndicator: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
  },
};

// Inject responsive styles for the ioGrid and vizGrid
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style');
  styleEl.textContent = `
    @media (max-width: 768px) {
      [style*="grid-template-columns"] {
        grid-template-columns: 1fr !important;
      }
    }
  `;
  document.head.appendChild(styleEl);
}
