import { useState, useCallback } from 'react';
import ProblemStatement from './components/ProblemStatement';
import AlgorithmVisualizer from './components/AlgorithmVisualizer';
import ControlPanel from './components/ControlPanel';
import CheckpointPanel from './components/CheckpointPanel';
import HintAnswerButtons from './components/HintAnswerButtons';
import DpSummaryTable from './components/DpSummaryTable';
import ActivityLog from './components/ActivityLog';
import { useAlgorithmSteps } from './hooks/useAlgorithmSteps';
import { useCheckpoint } from './hooks/useCheckpoint';
import { useActivityLog } from './hooks/useActivityLog';
import './App.css';

const DEFAULT_NUMS = [2, 7, 9, 3, 1];

export default function App() {
  const [customInput, setCustomInput] = useState(DEFAULT_NUMS.join(', '));
  const [nums, setNums] = useState(DEFAULT_NUMS);
  const { steps, dpFinal, finalAnswer } = useAlgorithmSteps(nums);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const { log, addLog } = useActivityLog();
  const { checkpointState, checkAnswer, showHint, showAnswer, resetCheckpoint } = useCheckpoint(currentStepIndex, addLog);

  const maxStepIndex = steps.length - 1;
  const isComplete = currentStepIndex === maxStepIndex && maxStepIndex >= 0;

  const goToStep = useCallback((newIndex) => {
    const clamped = Math.max(0, Math.min(newIndex, maxStepIndex));
    setCurrentStepIndex(clamped);
    addLog(`Navigated to step ${clamped} (house index ${steps[clamped]?.houseIndex ?? '?'})`);
  }, [maxStepIndex, steps, addLog]);

  const handleNext = useCallback(() => {
    goToStep(currentStepIndex + 1);
  }, [currentStepIndex, goToStep]);

  const handlePrev = useCallback(() => {
    goToStep(currentStepIndex - 1);
  }, [currentStepIndex, goToStep]);

  const handleReset = useCallback(() => {
    setCurrentStepIndex(0);
    addLog('Reset to step 0');
  }, [addLog]);

  const handleApplyCustomInput = useCallback(() => {
    const parsed = customInput
      .split(',')
      .map(s => s.trim())
      .filter(s => s !== '')
      .map(Number);
    
    if (parsed.length === 0 || parsed.some(isNaN)) {
      addLog('Invalid custom input. Please enter comma-separated integers.');
      return;
    }

    setNums(parsed);
    setCurrentStepIndex(0);
    addLog(`Applied custom input: [${parsed.join(', ')}]`);
  }, [customInput, addLog]);

  const handleResetToDefault = useCallback(() => {
    setNums(DEFAULT_NUMS);
    setCustomInput(DEFAULT_NUMS.join(', '));
    setCurrentStepIndex(0);
    addLog('Reset to default input');
  }, [addLog]);

  const currentStep = steps[currentStepIndex];

  if (!currentStep) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>House Robber</h1>
          <p className="algorithm-family">Algorithm Family: <strong>1D Dynamic Programming</strong></p>
        </header>
        <main className="container">
          <p>No steps available. Please provide a valid input array.</p>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>House Robber</h1>
        <p className="algorithm-family">Algorithm Family: <strong>1D Dynamic Programming</strong></p>
      </header>

      <main className="container">
        <ProblemStatement 
          inputArray={currentStep.nums} 
          finalAnswer={finalAnswer}
          revealAnswer={isComplete}
          customInput={customInput}
          onCustomInputChange={setCustomInput}
          onApplyCustomInput={handleApplyCustomInput}
          onResetToDefault={handleResetToDefault}
          isDefault={nums === DEFAULT_NUMS}
        />
        
        <section className="visualization-section">
          <h2>Algorithm Visualization</h2>
          <AlgorithmVisualizer step={currentStep} currentStepIndex={currentStepIndex} totalSteps={steps.length} />
          <ControlPanel
            currentStep={currentStepIndex}
            maxStep={maxStepIndex}
            onPrev={handlePrev}
            onNext={handleNext}
            onReset={handleReset}
            onGoToStep={goToStep}
          />
          <DpSummaryTable steps={steps} currentStepIndex={currentStepIndex} nums={currentStep.nums} />
        </section>

        <section className="interaction-section">
          <CheckpointPanel
            step={currentStep}
            checkpointState={checkpointState}
            onCheckAnswer={checkAnswer}
            onReset={resetCheckpoint}
          />
          <HintAnswerButtons
            onHint={showHint}
            onShowAnswer={showAnswer}
            hintVisible={checkpointState.hintVisible}
            answerVisible={checkpointState.answerVisible}
            answerValue={checkpointState.answerValue}
          />
        </section>

        <ActivityLog entries={log} />
      </main>
    </div>
  );
}