import React, { useState, useCallback, useRef, useEffect } from 'react';
import { trace, checkpoints, inputPoints, sortedPoints, expectedOutput } from './algorithm/trace';
import CanvasView from './components/CanvasView';
import StepControls from './components/StepControls';
import CheckpointCard from './components/CheckpointCard';
import ActivityLog from './components/ActivityLog';
import InputOutputPanel from './components/InputOutputPanel';
import './App.css';

// Learning objectives displayed alongside the activity log
const LEARNING_OBJECTIVES = [
  "Understand how Andrew's monotone chain achieves convex hull detection through alternating construction of upper and lower hulls.",
  "Predict the next operation based on the current point position and the lower/upper hull states.",
  "Identify invariants during convex hull construction, such as cross <= 0 indicating a need to backtrack.",
];

// Format a timestamp for the activity log
function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function App() {
  const totalSteps = trace.length;
  const [currentStep, setCurrentStep] = useState(0);
  const [activityLog, setActivityLog] = useState([
    { id: 0, time: formatTime(), type: 'system', message: 'Session started. Welcome to the Convex Hull interactive tutorial.' },
  ]);
  const [checkpointStates, setCheckpointStates] = useState(() => {
    const states = {};
    checkpoints.forEach((cp) => {
      states[cp.id] = { answered: false, correct: null, selectedKey: null, hintVisible: false, answerRevealed: false };
    });
    return states;
  });
  const [autoPlay, setAutoPlay] = useState(false);
  const autoPlayRef = useRef(null);
  const logIdRef = useRef(1);

  const addLogEntry = useCallback((type, message) => {
    const entry = { id: logIdRef.current++, time: formatTime(), type, message };
    setActivityLog((prev) => [...prev, entry]);
  }, []);

  const goToStep = useCallback(
    (step) => {
      const clamped = Math.max(0, Math.min(totalSteps - 1, step));
      if (clamped !== currentStep) {
        setCurrentStep(clamped);
        addLogEntry('navigate', `Navigated to Step ${clamped}: "${trace[clamped].title}"`);
      }
    },
    [currentStep, totalSteps, addLogEntry]
  );

  const nextStep = useCallback(() => {
    if (currentStep < totalSteps - 1) {
      const next = currentStep + 1;
      setCurrentStep(next);
      addLogEntry('navigate', `Advanced to Step ${next}: "${trace[next].title}"`);
    }
  }, [currentStep, totalSteps, addLogEntry]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      const prev = currentStep - 1;
      setCurrentStep(prev);
      addLogEntry('navigate', `Returned to Step ${prev}: "${trace[prev].title}"`);
    }
  }, [currentStep, addLogEntry]);

  // Auto-play logic
  useEffect(() => {
    if (autoPlay) {
      autoPlayRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= totalSteps - 1) {
            setAutoPlay(false);
            return prev;
          }
          return prev + 1;
        });
      }, 2200);
    } else {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    }
    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, [autoPlay, totalSteps]);

  // Log when auto-play toggles
  const toggleAutoPlay = useCallback(() => {
    setAutoPlay((prev) => {
      const next = !prev;
      addLogEntry('system', next ? 'Auto-play started' : 'Auto-play stopped');
      return next;
    });
  }, [addLogEntry]);

  const handleCheckpointAnswer = useCallback(
    (checkpointId, selectedKey) => {
      const cp = checkpoints.find((c) => c.id === checkpointId);
      if (!cp) return;
      const correct = selectedKey === cp.correctKey;
      setCheckpointStates((prev) => ({
        ...prev,
        [checkpointId]: { ...prev[checkpointId], answered: true, correct, selectedKey },
      }));
      addLogEntry(
        correct ? 'correct' : 'incorrect',
        `Checkpoint ${checkpointId}: ${correct ? 'Correct!' : 'Incorrect'} (selected "${selectedKey}")`
      );
    },
    [addLogEntry]
  );

  const handleShowHint = useCallback(
    (checkpointId) => {
      setCheckpointStates((prev) => ({
        ...prev,
        [checkpointId]: { ...prev[checkpointId], hintVisible: true },
      }));
      addLogEntry('hint', `Requested hint for Checkpoint ${checkpointId}`);
    },
    [addLogEntry]
  );

  const handleRevealAnswer = useCallback(
    (checkpointId) => {
      const cp = checkpoints.find((c) => c.id === checkpointId);
      if (!cp) return;
      setCheckpointStates((prev) => ({
        ...prev,
        [checkpointId]: { ...prev[checkpointId], answerRevealed: true, selectedKey: cp.correctKey, answered: true, correct: true },
      }));
      addLogEntry('reveal', `Revealed answer for Checkpoint ${checkpointId}: "${cp.correctKey}"`);
    },
    [addLogEntry]
  );

  const currentTrace = trace[currentStep];
  // Find active checkpoint for the current step
  const activeCheckpoint = checkpoints.find((cp) => cp.triggerStep === currentStep);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Convex Hull</h1>
        <span className="app-badge">Geometry / Scanline</span>
      </header>

      <InputOutputPanel
        inputPoints={inputPoints}
        sortedPoints={sortedPoints}
        expectedOutput={expectedOutput}
        currentTrace={currentTrace}
      />

      <div className="main-layout">
        <div className="viz-panel">
          <CanvasView
            trace={currentTrace}
            inputPoints={inputPoints}
            sortedPoints={sortedPoints}
            expectedOutput={expectedOutput}
          />
          <StepControls
            currentStep={currentStep}
            totalSteps={totalSteps}
            onPrev={prevStep}
            onNext={nextStep}
            onGoTo={goToStep}
            autoPlay={autoPlay}
            onToggleAutoPlay={toggleAutoPlay}
            phase={currentTrace.phase}
          />
        </div>

        <div className="side-panel">
          <div className="step-info card">
            <div className="step-badge">
              Step {currentStep} of {totalSteps - 1}
            </div>
            <h2 className="step-title">{currentTrace.title}</h2>
            <p className="step-description">{currentTrace.description}</p>
            {currentTrace.crossInfo && (
              <div className="cross-detail">
                <span className="cross-label">Cross product: </span>
                <span className={`cross-value ${currentTrace.crossInfo.value > 0 ? 'positive' : 'negative'}`}>
                  {currentTrace.crossInfo.value > 0 ? '+' : ''}{currentTrace.crossInfo.value}
                </span>
                <span className="cross-decision">
                  {' '}\u2192 {currentTrace.crossInfo.decision === 'add' ? 'Keep (cross > 0)' : 'Pop (cross \u2264 0)'}
                </span>
              </div>
            )}
          </div>

          {activeCheckpoint && (
            <CheckpointCard
              checkpoint={activeCheckpoint}
              state={checkpointStates[activeCheckpoint.id]}
              onAnswer={handleCheckpointAnswer}
              onShowHint={handleShowHint}
              onRevealAnswer={handleRevealAnswer}
            />
          )}
        </div>
      </div>

      <div className="bottom-row">
        <div className="objectives-card">
          <div className="objectives-title">Learning Objectives</div>
          <ul className="objectives-list">
            {LEARNING_OBJECTIVES.map((obj, idx) => (
              <li key={idx}>{obj}</li>
            ))}
          </ul>
        </div>
        <ActivityLog entries={activityLog} />
      </div>
    </div>
  );
}