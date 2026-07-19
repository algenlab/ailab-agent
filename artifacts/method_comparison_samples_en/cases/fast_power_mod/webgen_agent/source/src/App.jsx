import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import Header from './components/Header';
import ProblemStatement from './components/ProblemStatement';
import Visualization from './components/Visualization';
import Checkpoints from './components/Checkpoints';
import LearningLog from './components/LearningLog';
import { generateSteps, computeResult } from './utils/algorithm';
import './App.css';

const PROBLEM = {
  base: 3,
  exponent: 5,
  mod: 13,
  expected: 9
};

function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const [revealedAnswer, setRevealedAnswer] = useState(false);
  const [logEntries, setLogEntries] = useState([]);
  const [completedCheckpoints, setCompletedCheckpoints] = useState({});
  const autoPlayRef = useRef(null);

  const steps = useMemo(() => generateSteps(PROBLEM.base, PROBLEM.exponent, PROBLEM.mod), []);
  const finalAnswer = useMemo(() => computeResult(PROBLEM.base, PROBLEM.exponent, PROBLEM.mod), []);

  const addLogEntry = useCallback((message) => {
    const entry = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toLocaleTimeString(),
      message
    };
    setLogEntries(prev => [...prev, entry]);
  }, []);

  const goToStep = useCallback((stepIndex) => {
    const clamped = Math.max(0, Math.min(stepIndex, steps.length - 1));
    setCurrentStep(clamped);
    if (clamped > 0) {
      addLogEntry(`Navigated to step ${clamped} of ${steps.length - 1}`);
    } else {
      addLogEntry('Reset to initial state');
    }
  }, [steps.length, addLogEntry]);

  const nextStep = useCallback(() => {
    if (currentStep < steps.length - 1) {
      goToStep(currentStep + 1);
    }
  }, [currentStep, steps.length, goToStep]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      goToStep(currentStep - 1);
    }
  }, [currentStep, goToStep]);

  const reset = useCallback(() => {
    setAutoPlay(false);
    goToStep(0);
    setRevealedAnswer(false);
    addLogEntry('Visualization reset to beginning');
  }, [goToStep, addLogEntry]);

  // Auto-play
  useEffect(() => {
    if (autoPlay && currentStep < steps.length - 1) {
      autoPlayRef.current = setTimeout(() => {
        nextStep();
      }, 1200);
    } else if (currentStep >= steps.length - 1) {
      setAutoPlay(false);
    }
    return () => {
      if (autoPlayRef.current) clearTimeout(autoPlayRef.current);
    };
  }, [autoPlay, currentStep, steps.length, nextStep]);

  const toggleAutoPlay = () => {
    setAutoPlay(prev => {
      const newVal = !prev;
      addLogEntry(newVal ? 'Auto-play started' : 'Auto-play stopped');
      return newVal;
    });
  };

  const handleShowAnswer = () => {
    setRevealedAnswer(true);
    addLogEntry('Answer revealed: ' + finalAnswer);
  };

  const handleHint = () => {
    addLogEntry('Hint requested for visualization');
  };

  const handleCheckpointComplete = (questionId, questionTitle, correct) => {
    setCompletedCheckpoints(prev => ({ ...prev, [questionId]: correct }));
    addLogEntry(`Question "${questionTitle}" answered - ${correct ? 'Correct ✓' : 'Incorrect ✗'}`);
  };

  return (
    <div className="app">
      <Header title="Fast Power Modulo" family="Mathematics & Bitwise Operations" />
      <main className="main-content">
        <div className="left-column">
          <ProblemStatement
            base={PROBLEM.base}
            exponent={PROBLEM.exponent}
            mod={PROBLEM.mod}
            expected={PROBLEM.expected}
            answer={finalAnswer}
            revealed={revealedAnswer}
            onReveal={handleShowAnswer}
          />
          <Visualization
            steps={steps}
            currentStep={currentStep}
            onNext={nextStep}
            onPrev={prevStep}
            onReset={reset}
            autoPlay={autoPlay}
            onToggleAuto={toggleAutoPlay}
            onStep={goToStep}
            onShowAnswer={handleShowAnswer}
            onHint={handleHint}
            revealed={revealedAnswer}
          />
          <Checkpoints
            base={PROBLEM.base}
            exponent={PROBLEM.exponent}
            mod={PROBLEM.mod}
            expected={PROBLEM.expected}
            steps={steps}
            completed={completedCheckpoints}
            onComplete={handleCheckpointComplete}
          />
        </div>
        <div className="right-column">
          <LearningLog entries={logEntries} />
        </div>
      </main>
      <footer className="footer">
        <p>Interactive Explorer for Learning the Fast Power Modulo Algorithm</p>
      </footer>
    </div>
  );
}

export default App;