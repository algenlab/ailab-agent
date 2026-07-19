import React, { useState, useCallback, useRef, useEffect } from 'react';
import { problemData, algorithmSteps, checkpoints, stepCheckpointsMap } from './data/algorithmData';
import ArrayVisualizer from './components/ArrayVisualizer';
import CheckpointPanel from './components/CheckpointPanel';
import LearningLog from './components/LearningLog';

function formatTimestamp() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const s = String(now.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

let logIdCounter = 0;
function nextLogId() {
  logIdCounter += 1;
  return `log-${logIdCounter}`;
}

export default function App() {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [checkpointStates, setCheckpointStates] = useState({});
  const [learningLog, setLearningLog] = useState(() => [
    {
      id: nextLogId(),
      timestamp: formatTimestamp(),
      type: 'session_start',
      description: 'Session started. Problem loaded: Two Sum in Sorted Array. nums=[1,2,4,6,10], target=8.'
    }
  ]);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const autoPlayRef = useRef(null);
  const currentStepIndexRef = useRef(0);

  // Keep ref in sync with state
  useEffect(() => {
    currentStepIndexRef.current = currentStepIndex;
  }, [currentStepIndex]);

  const currentStep = algorithmSteps[currentStepIndex];
  const activeCheckpointIds = stepCheckpointsMap[currentStepIndex] || [];
  const activeCheckpoints = activeCheckpointIds.map(id => checkpoints[id]).filter(Boolean);

  const addLogEntry = useCallback((type, description) => {
    setLearningLog(prev => [
      ...prev.slice(-99), // Keep max 100 entries to avoid memory issues
      {
        id: nextLogId(),
        timestamp: formatTimestamp(),
        type,
        description
      }
    ]);
  }, []);

  const goToStep = useCallback((stepIndex) => {
    if (stepIndex < 0 || stepIndex >= algorithmSteps.length) return;
    setCurrentStepIndex(stepIndex);
    const step = algorithmSteps[stepIndex];
    const phaseLabel = step.phase === 'init' ? 'Initial state' : step.phase === 'searching' ? 'Searching' : 'Solution found';
    addLogEntry('navigation', `Navigated to Step ${step.id}: ${phaseLabel} — left=${step.leftIdx}, right=${step.rightIdx}, sum=${step.sum}.`);
  }, [addLogEntry]);

  const handleNext = useCallback(() => {
    if (currentStepIndex < algorithmSteps.length - 1) {
      goToStep(currentStepIndex + 1);
    }
  }, [currentStepIndex, goToStep]);

  const handlePrev = useCallback(() => {
    if (currentStepIndex > 0) {
      goToStep(currentStepIndex - 1);
    }
  }, [currentStepIndex, goToStep]);

  const handleReset = useCallback(() => {
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
    setAutoPlaying(false);
    setCurrentStepIndex(0);
    currentStepIndexRef.current = 0;
    setCheckpointStates({});
    setLearningLog([
      {
        id: nextLogId(),
        timestamp: formatTimestamp(),
        type: 'reset',
        description: 'Session reset. All progress cleared. Starting fresh.'
      }
    ]);
  }, []);

  const toggleAutoPlay = useCallback(() => {
    // Clear any existing interval first
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
    setAutoPlaying(prev => {
      const newState = !prev;
      if (newState) {
        addLogEntry('navigation', 'Auto-play started.');
        autoPlayRef.current = setInterval(() => {
          const prevStep = currentStepIndexRef.current;
          if (prevStep >= algorithmSteps.length - 1) {
            clearInterval(autoPlayRef.current);
            autoPlayRef.current = null;
            setAutoPlaying(false);
            return;
          }
          const nextStep = prevStep + 1;
          setCurrentStepIndex(nextStep);
          currentStepIndexRef.current = nextStep;
          const step = algorithmSteps[nextStep];
          const phaseLabel = step.phase === 'init' ? 'Initial state' : step.phase === 'searching' ? 'Searching' : 'Solution found';
          setLearningLog(entries => {
            const newEntries = [
              ...entries.slice(-99),
              {
                id: nextLogId(),
                timestamp: formatTimestamp(),
                type: 'navigation',
                description: `Auto-play: Step ${step.id} — ${phaseLabel} — left=${step.leftIdx}, right=${step.rightIdx}, sum=${step.sum}.`
              }
            ];
            return newEntries;
          });
        }, 3000);
      } else {
        addLogEntry('navigation', 'Auto-play stopped.');
      }
      return newState;
    });
  }, [addLogEntry]);

  // Clean up auto-play interval on unmount
  useEffect(() => {
    return () => {
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current);
        autoPlayRef.current = null;
      }
    };
  }, []);

  const handleManualNavigation = useCallback((stepIndex) => {
    // Stop auto-play on any manual interaction
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
    if (autoPlaying) {
      setAutoPlaying(false);
      addLogEntry('navigation', 'Auto-play interrupted by manual navigation.');
    }
    setCurrentStepIndex(stepIndex);
    currentStepIndexRef.current = stepIndex;
    const step = algorithmSteps[stepIndex];
    const phaseLabel = step.phase === 'init' ? 'Initial state' : step.phase === 'searching' ? 'Searching' : 'Solution found';
    addLogEntry('navigation', `Navigated to Step ${step.id}: ${phaseLabel} — left=${step.leftIdx}, right=${step.rightIdx}, sum=${step.sum}.`);
  }, [autoPlaying, addLogEntry]);

  const handleSelectAnswer = useCallback((checkpointId, selectedOption, isCorrect) => {
    setCheckpointStates(prev => ({
      ...prev,
      [checkpointId]: {
        ...prev[checkpointId],
        answered: true,
        selectedOption,
        isCorrect
      }
    }));
    const cp = checkpoints[checkpointId];
    const optionLabel = String.fromCharCode(65 + selectedOption);
    addLogEntry(
      isCorrect ? 'answer_correct' : 'answer_incorrect',
      `${cp.title}: Selected option ${optionLabel}. ${isCorrect ? 'Correct!' : 'Incorrect.'}`
    );
  }, [addLogEntry]);

  const handleRevealHint = useCallback((checkpointId) => {
    setCheckpointStates(prev => ({
      ...prev,
      [checkpointId]: {
        ...prev[checkpointId],
        hintRevealed: true
      }
    }));
    const cp = checkpoints[checkpointId];
    addLogEntry('hint', `Hint revealed for "${cp.title}".`);
  }, [addLogEntry]);

  const handleRevealAnswer = useCallback((checkpointId) => {
    setCheckpointStates(prev => ({
      ...prev,
      [checkpointId]: {
        ...prev[checkpointId],
        answerRevealed: true,
        answered: true,
        selectedOption: checkpoints[checkpointId].correctIndex,
        isCorrect: true
      }
    }));
    const cp = checkpoints[checkpointId];
    addLogEntry('show_answer', `Answer revealed for "${cp.title}".`);
  }, [addLogEntry]);

  const handleDismissFeedback = useCallback((checkpointId) => {
    // Feedback dismissal handled internally by CheckpointPanel
  }, []);

  const isLastStep = currentStepIndex === algorithmSteps.length - 1;
  const isFirstStep = currentStepIndex === 0;

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Two Sum in Sorted Array</h1>
        <span className="app-badge">Array Pointer / Window / Prefix</span>
      </header>

      <main className="app-main">
        <div className="main-content">
          {/* Problem Description */}
          <section className="problem-section card" aria-label="Problem description">
            <h2 className="section-title">Problem Statement</h2>
            <p className="problem-text">
              In an e-commerce promotion, as a product selection assistant, you need to find two items
              from a product list <code>nums</code> sorted in ascending order of price, such that their
              total price exactly equals the target voucher amount held by the user. Return the indices
              of these two items (0-indexed) as a list; if no such combination exists, return an empty list.
            </p>
            <div className="problem-io">
              <div className="io-block io-input">
                <h4 className="io-label">Input</h4>
                <pre className="io-code">{JSON.stringify({ nums: problemData.nums, target: problemData.target }, null, 2)}</pre>
              </div>
              <div className="io-block io-output">
                <h4 className="io-label">Expected Output</h4>
                <pre className="io-code io-answer">{JSON.stringify(problemData.expectedAnswer)}</pre>
                <p className="io-note">nums[1] + nums[3] = 2 + 6 = 8</p>
              </div>
            </div>
          </section>

          {/* Algorithm Visualization */}
          <section className="visualization-section card" aria-label="Algorithm visualization">
            <h2 className="section-title">Step-by-Step Visualization</h2>

            <ArrayVisualizer
              nums={problemData.nums}
              leftIdx={currentStep.leftIdx}
              rightIdx={currentStep.rightIdx}
              sum={currentStep.sum}
              target={problemData.target}
              compareResult={currentStep.compareResult}
              isFound={currentStep.isFound}
              actionText={currentStep.actionText}
              stepId={currentStep.id}
            />

            {/* Step Navigation Controls */}
            <div className="step-controls" role="toolbar" aria-label="Step navigation controls">
              <button
                className="btn btn-nav"
                onClick={() => handleManualNavigation(0)}
                disabled={isFirstStep}
                aria-label="Go to first step"
                title="First Step"
              >
                «
              </button>
              <button
                className="btn btn-nav"
                onClick={() => handleManualNavigation(currentStepIndex - 1)}
                disabled={isFirstStep}
                aria-label="Previous step"
                title="Previous Step"
              >
                ‹ Prev
              </button>
              <span className="step-indicator" aria-live="polite" aria-atomic="true">
                Step {currentStep.id} of {algorithmSteps.length - 1}
              </span>
              <button
                className="btn btn-nav"
                onClick={() => handleManualNavigation(currentStepIndex + 1)}
                disabled={isLastStep}
                aria-label="Next step"
                title="Next Step"
              >
                Next ›
              </button>
              <button
                className="btn btn-nav"
                onClick={() => handleManualNavigation(algorithmSteps.length - 1)}
                disabled={isLastStep}
                aria-label="Go to last step"
                title="Last Step"
              >
                »
              </button>
              <button
                className={`btn btn-auto ${autoPlaying ? 'btn-auto-active' : ''}`}
                onClick={toggleAutoPlay}
                aria-label={autoPlaying ? 'Pause auto-play' : 'Start auto-play'}
                title={autoPlaying ? 'Pause' : 'Auto-play'}
              >
                {autoPlaying ? (
                  <span><span className="auto-icon" aria-hidden="true">▮▮</span> Pause</span>
                ) : (
                  <span><span className="auto-icon" aria-hidden="true">▶</span> Auto</span>
                )}
              </button>
              <button
                className="btn btn-reset"
                onClick={handleReset}
                aria-label="Reset"
                title="Reset"
              >
                ↺ Reset
              </button>
            </div>

            {/* Phase indicator */}
            <div className={`phase-indicator phase-${currentStep.phase}`} aria-label={`Current phase: ${currentStep.phase}`}>
              <span className="phase-dot" aria-hidden="true" />
              <span className="phase-label">
                {currentStep.phase === 'init' && 'Initial State — pointers at both ends'}
                {currentStep.phase === 'searching' && 'Searching — narrowing the window'}
                {currentStep.phase === 'found' && 'Solution Found — target matched!'}
              </span>
            </div>
          </section>

          {/* Checkpoints */}
          <section className="checkpoints-section" aria-label="Checkpoint questions">
            {activeCheckpoints.length === 0 && (
              <div className="card checkpoint-placeholder">
                <p>No checkpoint questions for this step. Use the navigation to explore the algorithm steps.</p>
              </div>
            )}
            {activeCheckpoints.map((cp) => (
              <div key={cp.id} className="card checkpoint-card">
                <CheckpointPanel
                  checkpoint={cp}
                  checkpointState={checkpointStates[cp.id] || {}}
                  onSelectAnswer={handleSelectAnswer}
                  onRevealHint={handleRevealHint}
                  onRevealAnswer={handleRevealAnswer}
                  onDismissFeedback={handleDismissFeedback}
                />
              </div>
            ))}
          </section>

          {/* Learning Objectives */}
          <section className="objectives-section card" aria-label="Learning objectives">
            <h2 className="section-title">Learning Objectives</h2>
            <ul className="objectives-list">
              <li>Understand the state transition of the two-pointer method in an ascending price list, where the movement direction is determined by comparing the current sum with the target.</li>
              <li>Identify the invariant that the left pointer increases and the right pointer decreases, and the shrinking nature of the search interval.</li>
              <li>Be able to predict the next pointer movement based on any step's nums[left], nums[right], and sum.</li>
            </ul>
          </section>
        </div>

        {/* Sidebar: Learning Log */}
        <aside className="sidebar">
          <LearningLog entries={learningLog} />
        </aside>
      </main>

      <footer className="app-footer">
        <p>Interactive Algorithm Learning — Two Sum in Sorted Array — Array Pointer / Window / Prefix</p>
      </footer>
    </div>
  );
}