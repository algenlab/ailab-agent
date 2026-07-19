import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { generateSteps, buildCheckpoints } from './data/algorithmData';
import ProblemDisplay from './components/ProblemDisplay';
import DpTable from './components/DpTable';
import CheckpointPanel from './components/CheckpointPanel';
import LearningLog from './components/LearningLog';
import StepNavigation from './components/StepNavigation';

// Problem configuration — fixed as specified
const PROBLEM = {
  amount: 11,
  coins: [1, 2, 5]
};

export default function App() {
  // Pre-compute all steps once
  const { steps, finalAnswer } = useMemo(
    () => generateSteps(PROBLEM.amount, PROBLEM.coins),
    []
  );
  const { checkpointMap } = useMemo(() => buildCheckpoints(steps), [steps]);

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const [learningLog, setLearningLog] = useState([]);
  const [checkpointAnswers, setCheckpointAnswers] = useState({});
  const [checkpointHints, setCheckpointHints] = useState({});
  const [checkpointReveals, setCheckpointReveals] = useState({});
  const autoPlayRef = useRef(null);
  const lastLoggedCheckpointRef = useRef({});
  const hasInitializedRef = useRef(false);

  const currentStep = steps[currentStepIndex];
  const activeCheckpoint = checkpointMap[currentStep.id] || null;

  // Log checkpoint-reached events
  useEffect(() => {
    if (activeCheckpoint && !lastLoggedCheckpointRef.current[activeCheckpoint.id]) {
      lastLoggedCheckpointRef.current[activeCheckpoint.id] = true;
      addLogEntry('checkpoint-reached', `Reached checkpoint: "${activeCheckpoint.title}"`);
    }
  }, [activeCheckpoint]);

  // Auto-play logic
  useEffect(() => {
    if (autoPlay) {
      autoPlayRef.current = setInterval(() => {
        setCurrentStepIndex(prev => {
          if (prev >= steps.length - 1) {
            setAutoPlay(false);
            return prev;
          }
          return prev + 1;
        });
      }, 800);
    } else {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    }
    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, [autoPlay, steps.length]);

  const addLogEntry = useCallback((type, message) => {
    setLearningLog(prev => [...prev, { type, message, timestamp: Date.now() }]);
  }, []);

  // Log initial step only once, despite StrictMode double-mount
  useEffect(() => {
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      addLogEntry('navigate', 'Page loaded. Viewing initial DP state.');
    }
  }, [addLogEntry]);

  const handlePrev = useCallback(() => {
    setCurrentStepIndex(prev => Math.max(0, prev - 1));
    setAutoPlay(false);
    addLogEntry('navigate', `Moved to step ${currentStepIndex} (previous)`);
  }, [currentStepIndex, addLogEntry]);

  const handleNext = useCallback(() => {
    setCurrentStepIndex(prev => Math.min(steps.length - 1, prev + 1));
    setAutoPlay(false);
    addLogEntry('navigate', `Moved to step ${currentStepIndex + 2} (next)`);
  }, [currentStepIndex, steps.length, addLogEntry]);

  const handleGoTo = useCallback((index) => {
    setCurrentStepIndex(index);
    setAutoPlay(false);
    addLogEntry('navigate', `Jumped to step ${index + 1}`);
  }, [addLogEntry]);

  const handleToggleAutoPlay = useCallback(() => {
    setAutoPlay(prev => !prev);
    if (!autoPlay) {
      addLogEntry('navigate', 'Started auto-play');
    } else {
      addLogEntry('navigate', 'Paused auto-play');
    }
  }, [autoPlay, addLogEntry]);

  const handleCheckpointAnswer = useCallback((checkpointId, selectedOption) => {
    // Find the checkpoint object from the map
    const checkpointEntries = Object.entries(checkpointMap);
    const found = checkpointEntries.find(([, cp]) => cp.id === checkpointId);
    const cp = found ? found[1] : null;
    if (!cp) return;

    const isCorrect = selectedOption === cp.correctIndex;
    setCheckpointAnswers(prev => ({ ...prev, [checkpointId]: isCorrect ? 'correct' : 'incorrect' }));
    addLogEntry(
      isCorrect ? 'correct' : 'incorrect',
      `${isCorrect ? 'Correct' : 'Incorrect'} answer for checkpoint: "${cp.title}" — selected option ${selectedOption + 1}`
    );
  }, [checkpointMap, addLogEntry]);

  const handleHint = useCallback((checkpointId) => {
    setCheckpointHints(prev => ({ ...prev, [checkpointId]: true }));
    addLogEntry('hint', 'Used hint for checkpoint');
  }, [addLogEntry]);

  const handleShowAnswer = useCallback((checkpointId) => {
    setCheckpointReveals(prev => ({ ...prev, [checkpointId]: true }));
    // Also mark as answered if not already
    const checkpointEntries = Object.entries(checkpointMap);
    const found = checkpointEntries.find(([, cp]) => cp.id === checkpointId);
    const cp = found ? found[1] : null;
    if (cp && !checkpointAnswers[checkpointId]) {
      setCheckpointAnswers(prev => ({ ...prev, [checkpointId]: 'revealed' }));
    }
    addLogEntry('reveal', 'Revealed answer for checkpoint');
  }, [checkpointMap, checkpointAnswers, addLogEntry]);

  const isAtFinalStep = currentStepIndex === steps.length - 1;

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Complete Knapsack Coin Change</h1>
        <span className="algorithm-badge">DP Core Extension — Unbounded Knapsack</span>
      </header>

      <main className="app-main">
        <section className="top-section">
          <ProblemDisplay
            amount={PROBLEM.amount}
            coins={PROBLEM.coins}
            finalAnswer={finalAnswer}
          />

          <div className="strategy-box">
            <h4>Strategy</h4>
            <p>Update <code>dp[c]</code> in <strong>increasing capacity order</strong>, allowing the same coin to be reused. For each coin, iterate from the coin's value up to the target amount, checking if using this coin improves the solution.</p>
          </div>
        </section>

        <section className="viz-section">
          <DpTable
            dp={currentStep.dp}
            highlightIndex={currentStep.highlightIndex}
            referenceIndex={currentStep.referenceIndex}
            coin={currentStep.coin}
            capacity={currentStep.capacity}
            changed={currentStep.changed}
            amount={PROBLEM.amount}
          />
        </section>

        <section className="checkpoint-section">
          {activeCheckpoint && (
            <CheckpointPanel
              checkpoint={activeCheckpoint}
              onAnswer={handleCheckpointAnswer}
              onHint={handleHint}
              onShowAnswer={handleShowAnswer}
              answered={!!checkpointAnswers[activeCheckpoint.id]}
              answerResult={checkpointAnswers[activeCheckpoint.id] || null}
              hintVisible={!!checkpointHints[activeCheckpoint.id]}
              showAnswerVisible={!!checkpointReveals[activeCheckpoint.id]}
            />
          )}
          {isAtFinalStep && !activeCheckpoint && (
            <div className="completion-banner">
              Algorithm complete! Final answer: <strong>{finalAnswer} coin{finalAnswer !== 1 ? 's' : ''}</strong> for amount {PROBLEM.amount}. Review the learning log below for a summary of your activity.
            </div>
          )}
        </section>

        <section className="nav-section">
          <StepNavigation
            currentStepIndex={currentStepIndex}
            totalSteps={steps.length}
            currentStep={currentStep}
            onPrev={handlePrev}
            onNext={handleNext}
            onGoTo={handleGoTo}
            autoPlay={autoPlay}
            onToggleAutoPlay={handleToggleAutoPlay}
          />
        </section>

        <section className="learning-objectives">
          <h3 className="section-title">Learning Objectives</h3>
          <ul>
            <li>Understand that <code>dp[capacity]</code> represents the minimum number of coins to make up capacity.</li>
            <li>Analyze how the coin loop and increasing capacity order allow coin reuse.</li>
            <li>Be able to predict the next dp update based on the current dp state and coin denomination.</li>
          </ul>
        </section>

        <section className="log-section">
          <LearningLog entries={learningLog} />
        </section>
      </main>

      <footer className="app-footer">
        <p>Interactive DP Algorithm Visualizer — No backend services required. All computation runs locally in your browser.</p>
      </footer>
    </div>
  );
}
