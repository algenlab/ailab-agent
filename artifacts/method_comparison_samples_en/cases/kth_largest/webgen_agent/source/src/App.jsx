import React, { useState, useMemo, useCallback } from 'react';
import InputDisplay from './components/InputDisplay';
import HeapVisualizer from './components/HeapVisualizer';
import StepControls from './components/StepControls';
import Checkpoint from './components/Checkpoint';
import LearningLog from './components/LearningLog';
import { computeSteps } from './utils/computeSteps';

const PROBLEM_INPUT = {
  k: 2,
  nums: [3, 2, 1, 5, 6, 4]
};

export default function App() {
  const { steps, finalAnswer } = useMemo(() => computeSteps(PROBLEM_INPUT.nums, PROBLEM_INPUT.k), []);
  const totalSteps = steps.length;
  const [currentStep, setCurrentStep] = useState(1);
  const [logEntries, setLogEntries] = useState([]);

  const addLog = useCallback(({ type, action }) => {
    setLogEntries(prev => [
      ...prev,
      {
        timestamp: Date.now(),
        message: action,
        type
      }
    ]);
  }, []);

  const handlePrev = () => {
    if (currentStep > 1) {
      const next = currentStep - 1;
      setCurrentStep(next);
      addLog({ type: 'navigation', action: `Navigated to step ${next}.` });
    }
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      const next = currentStep + 1;
      setCurrentStep(next);
      addLog({ type: 'navigation', action: `Navigated to step ${next}.` });
    }
  };

  const handleReset = () => {
    setCurrentStep(1);
    addLog({ type: 'navigation', action: 'Reset to step 1.' });
  };

  const currentStepData = steps[currentStep - 1] || null;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Kth Largest Element in an Array</h1>
        <span className="algorithm-family">Algorithm: Heap / TopK</span>
      </header>

      <main className="main-content">
        <section className="visualization-section">
          <InputDisplay input={PROBLEM_INPUT} finalAnswer={finalAnswer} />
          <StepControls
            currentStep={currentStep}
            totalSteps={totalSteps}
            onPrev={handlePrev}
            onNext={handleNext}
            onReset={handleReset}
            stepIndex={currentStepData?.num}
          />
          {currentStepData && (
            <HeapVisualizer
              heapBefore={currentStepData.heapBefore}
              heapAfter={currentStepData.heapAfter}
              topBefore={currentStepData.topBefore}
              topAfter={currentStepData.topAfter}
              action={currentStepData.action}
              reason={currentStepData.reason}
            />
          )}
        </section>

        <aside className="side-panel">
          <Checkpoint onLog={addLog} />
          <LearningLog entries={logEntries} />
        </aside>
      </main>

      <footer className="app-footer">
        <p>Interactive learning tool – all processing is local.</p>
      </footer>
    </div>
  );
}
  