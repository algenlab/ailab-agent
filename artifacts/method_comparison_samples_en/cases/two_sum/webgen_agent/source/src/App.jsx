import React, { useState, useCallback, useRef, useEffect } from 'react';
import ProblemHeader from './components/ProblemHeader';
import AlgorithmVisualizer from './components/AlgorithmVisualizer';
import CheckpointPanel from './components/CheckpointPanel';
import ActivityLog from './components/ActivityLog';
import { useActivityLog } from './hooks/useActivityLog';
import { createInitialState, computeNextStep, computeAllSteps } from './logic/twoSumLogic';
import './App.css';

const PROBLEM_INPUT = {
  nums: [2, 7, 11, 15],
  target: 9
};

const EXPECTED_ANSWER = [0, 1];

export default function App() {
  const { logEntries, addEntry } = useActivityLog();
  const [algorithmState, setAlgorithmState] = useState(() => createInitialState(PROBLEM_INPUT));
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [customNums, setCustomNums] = useState(null);

  const allSteps = computeAllSteps(customNums || PROBLEM_INPUT);

  const goToStep = useCallback((stepIndex) => {
    if (stepIndex < -1 || stepIndex >= allSteps.length) return;
    setCurrentStepIndex(stepIndex);
    setShowHint(false);
    setShowAnswer(false);
    if (stepIndex === -1) {
      setAlgorithmState(createInitialState(customNums || PROBLEM_INPUT));
      addEntry({ type: 'navigation', message: 'Reset to initial state.' });
    } else {
      setAlgorithmState(allSteps[stepIndex]);
      addEntry({ type: 'navigation', message: `Navigated to step ${stepIndex + 1} of ${allSteps.length}.` });
    }
  }, [allSteps, customNums, PROBLEM_INPUT, addEntry]);

  const stepForward = useCallback(() => {
    if (currentStepIndex < allSteps.length - 1) {
      goToStep(currentStepIndex + 1);
    }
  }, [currentStepIndex, allSteps.length, goToStep]);

  const stepBackward = useCallback(() => {
    if (currentStepIndex >= -1) {
      goToStep(currentStepIndex - 1);
    }
  }, [currentStepIndex, goToStep]);

  const handleCheckpointAnswer = useCallback((isCorrect, message) => {
    addEntry({
      type: 'checkpoint',
      message: message,
      correct: isCorrect
    });
  }, [addEntry]);

  const handleHintRequest = useCallback(() => {
    setShowHint(true);
    addEntry({ type: 'hint', message: 'Hint requested for the current checkpoint.' });
  }, [addEntry]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    addEntry({ type: 'reveal', message: 'Answer revealed for the current checkpoint.' });
  }, [addEntry]);

  const handleResetAll = useCallback(() => {
    setCustomNums(null);
    setCurrentStepIndex(-1);
    setAlgorithmState(createInitialState(PROBLEM_INPUT));
    setShowHint(false);
    setShowAnswer(false);
    addEntry({ type: 'navigation', message: 'Full reset: restored original problem input.' });
  }, [addEntry]);

  const handleCustomInput = useCallback(() => {
    const newNums = {
      nums: [3, 2, 4],
      target: 6
    };
    setCustomNums(newNums);
    setCurrentStepIndex(-1);
    setAlgorithmState(createInitialState(newNums));
    setShowHint(false);
    setShowAnswer(false);
    addEntry({ type: 'navigation', message: 'Switched to custom input: nums=[3,2,4], target=6.' });
  }, [addEntry]);

  const handleAltInput = useCallback(() => {
    const newNums = {
      nums: [2, 8, 11, 15],
      target: 9
    };
    setCustomNums(newNums);
    setCurrentStepIndex(-1);
    setAlgorithmState(createInitialState(newNums));
    setShowHint(false);
    setShowAnswer(false);
    addEntry({ type: 'navigation', message: 'Switched to alternate input: nums=[2,8,11,15], target=9 (nums[1] changed to 8).' });
  }, [addEntry]);

  const effectiveInput = customNums || PROBLEM_INPUT;

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Two Sum</h1>
        <span className="app-family">Hash Table / Map</span>
      </header>

      <ProblemHeader
        input={effectiveInput}
        expectedAnswer={customNums ? computeExpected(customNums) : EXPECTED_ANSWER}
        customNums={customNums}
        onReset={handleResetAll}
        onCustomInput={handleCustomInput}
        onAltInput={handleAltInput}
      />

      <div className="app-main">
        <div className="app-left">
          <AlgorithmVisualizer
            state={algorithmState}
            stepIndex={currentStepIndex}
            totalSteps={allSteps.length}
            onForward={stepForward}
            onBackward={stepBackward}
            allSteps={allSteps}
          />

          <CheckpointPanel
            currentStepIndex={currentStepIndex}
            allSteps={allSteps}
            input={effectiveInput}
            showHint={showHint}
            showAnswer={showAnswer}
            onAnswer={handleCheckpointAnswer}
            onHint={handleHintRequest}
            onShowAnswer={handleShowAnswer}
          />
        </div>

        <div className="app-right">
          <ActivityLog entries={logEntries} />
        </div>
      </div>
    </div>
  );
}

function computeExpected(input) {
  const { nums, target } = input;
  const seen = {};
  for (let i = 0; i < nums.length; i++) {
    const need = target - nums[i];
    if (need in seen) {
      return [seen[need], i];
    }
    seen[nums[i]] = i;
  }
  return [];
}