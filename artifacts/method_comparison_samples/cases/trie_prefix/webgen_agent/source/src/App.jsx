import React, { useState, useCallback, useRef, useMemo } from 'react';
import ProblemStatement from './components/ProblemStatement';
import TrieVisualization from './components/TrieVisualization';
import StepNavigator from './components/StepNavigator';
import CheckpointPanel from './components/CheckpointPanel';
import ActivityLog from './components/ActivityLog';
import HintPanel from './components/HintPanel';
import { buildTrieTrace, PROBLEM_INPUT, PROBLEM_ANSWER } from './trieEngine';
import './App.css';

export default function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [logEntries, setLogEntries] = useState([]);
  const [checkpointResult, setCheckpointResult] = useState(null);
  const [checkpointValue, setCheckpointValue] = useState('');
  const logIdRef = useRef(0);

  const trace = useMemo(() => buildTrieTrace(PROBLEM_INPUT), []);
  const TOTAL_STEPS = trace.totalSteps - 1;

  const addLog = useCallback((message, type = 'info') => {
    logIdRef.current += 1;
    const entry = { id: logIdRef.current, message, type, time: new Date().toLocaleTimeString() };
    setLogEntries(prev => [entry, ...prev]);
  }, []);

  const handleStepChange = useCallback((step) => {
    const clamped = Math.max(0, Math.min(TOTAL_STEPS, step));
    setCurrentStep(clamped);
    setShowAnswer(false);
    setShowHint(false);
    setCheckpointResult(null);
    setCheckpointValue('');
    const stepInfo = trace.steps[clamped];
    if (stepInfo) {
      addLog(`导航到步骤 ${clamped}: ${stepInfo.label}`, 'info');
    }
  }, [trace, addLog, TOTAL_STEPS]);

  const handleShowHint = useCallback(() => {
    setShowHint(prev => !prev);
    if (!showHint) {
      addLog('💡 查看了提示', 'hint');
    }
  }, [addLog, showHint]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    setCurrentStep(TOTAL_STEPS);
    setShowHint(false);
    addLog('🔍 查看了最终答案', 'answer');
  }, [addLog, TOTAL_STEPS]);

  const handleReset = useCallback(() => {
    setCurrentStep(0);
    setShowAnswer(false);
    setShowHint(false);
    setCheckpointResult(null);
    setCheckpointValue('');
    addLog('🔄 重置了所有状态', 'info');
  }, [addLog]);

  const handleCheckpointSubmit = useCallback(() => {
    const trimmed = checkpointValue.trim();
    if (!trimmed) return;
    if (trimmed === '3' || trimmed === '三') {
      setCheckpointResult('correct');
      addLog('✅ 预测正确！prefix="ap" 匹配到 3 个单词', 'correct');
    } else {
      setCheckpointResult('incorrect');
      addLog(`❌ 预测错误：你输入了 "${trimmed}"，正确答案是 3`, 'incorrect');
    }
  }, [checkpointValue, addLog]);

  const handleCheckpointRetry = useCallback(() => {
    setCheckpointResult(null);
    setCheckpointValue('');
  }, []);

  const stepData = trace.steps[currentStep] || trace.steps[0];

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">Trie 前缀计数</h1>
        <span className="app-badge">交互式算法教学</span>
      </header>

      <div className="app-layout">
        <div className="main-column">
          <ProblemStatement
            input={PROBLEM_INPUT}
            answer={PROBLEM_ANSWER}
            showAnswer={showAnswer}
          />

          <TrieVisualization
            stepData={stepData}
            currentStep={currentStep}
            totalSteps={TOTAL_STEPS}
            trace={trace}
          />

          <StepNavigator
            currentStep={currentStep}
            totalSteps={TOTAL_STEPS}
            onStepChange={handleStepChange}
            onShowHint={handleShowHint}
            onShowAnswer={handleShowAnswer}
            onReset={handleReset}
            showAnswer={showAnswer}
            showHint={showHint}
          />
        </div>

        <div className="side-column">
          <CheckpointPanel
            result={checkpointResult}
            value={checkpointValue}
            onValueChange={setCheckpointValue}
            onSubmit={handleCheckpointSubmit}
            onRetry={handleCheckpointRetry}
          />

          {showHint && (
            <HintPanel
              currentStep={currentStep}
              onDismiss={() => setShowHint(false)}
            />
          )}

          <ActivityLog entries={logEntries} />
        </div>
      </div>
    </div>
  );
}
