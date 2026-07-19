import React, { useState, useCallback, useRef } from 'react';
import ProblemHeader from './components/ProblemHeader';
import InputDisplay from './components/InputDisplay';
import Visualizer from './components/Visualizer';
import PredictionPanel from './components/PredictionPanel';
import ActivityLog from './components/ActivityLog';
import { generateSteps, initialState as initialProblemState } from './logic/binarySearch';
import './App.css';

export default function App() {
  const [problemState] = useState(() => ({ ...initialProblemState }));
  const steps = useRef(generateSteps(problemState.nums, problemState.target)).current;
  const [currentStep, setCurrentStep] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [hintVisible, setHintVisible] = useState(false);
  const [hintLevel, setHintLevel] = useState(0);
  const [activityLog, setActivityLog] = useState([]);
  const logIdRef = useRef(0);

  const addLog = useCallback((type, message) => {
    logIdRef.current += 1;
    const entry = {
      id: logIdRef.current,
      type,
      message,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false })
    };
    setActivityLog(prev => [entry, ...prev]);
  }, []);

  const handleStepChange = useCallback((step) => {
    setCurrentStep(step);
    setShowAnswer(false);
    setHintVisible(false);
    setHintLevel(0);
    addLog('navigation', `跳转到步骤 ${step + 1}`);
  }, [addLog]);

  const handlePrev = useCallback(() => {
    setCurrentStep(s => Math.max(0, s - 1));
    setShowAnswer(false);
    setHintVisible(false);
    setHintLevel(0);
    addLog('navigation', '上一步');
  }, [addLog]);

  const handleNext = useCallback(() => {
    setCurrentStep(s => Math.min(steps.length - 1, s + 1));
    setShowAnswer(false);
    setHintVisible(false);
    setHintLevel(0);
    addLog('navigation', '下一步');
  }, [steps.length, addLog]);

  const handleReset = useCallback(() => {
    setCurrentStep(0);
    setShowAnswer(false);
    setHintVisible(false);
    setHintLevel(0);
    addLog('action', '重置演示');
  }, [addLog]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    addLog('action', `查看了最终答案: ${problemState.answer}`);
  }, [addLog, problemState.answer]);

  const handleGuess = useCallback((isCorrect) => {
    if (isCorrect) {
      addLog('correct', '猜对了答案！');
    } else {
      addLog('incorrect', '猜测答案不正确');
    }
  }, [addLog]);

  const handleHint = useCallback(() => {
    const hints = [
      '提示 1: 二分查找的核心思想是每次比较中间元素，然后排除一半的搜索空间。',
      '提示 2: 当 nums[mid] < target 时，目标值在右半部分，需要移动 left 指针。',
      '提示 3: 当 nums[mid] > target 时，目标值在左半部分，需要移动 right 指针。',
      '最终提示: 对于 nums=[-1,0,3,5,9,12], target=9，中间值 3 < 9，所以在右半部分 [5,9,12] 继续查找。然后中间值 9 == 9，找到目标！索引为 4。'
    ];
    const lvl = hintLevel;
    if (lvl < hints.length) {
      setHintVisible(true);
      setHintLevel(lvl + 1);
      addLog('hint', `提示 ${lvl + 1}: ${hints[lvl]}`);
    }
    if (!hintVisible) setHintVisible(true);
  }, [hintLevel, hintVisible, addLog]);

  const step = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;
  const isFirstStep = currentStep === 0;

  return (
    <div className="app-container">
      <ProblemHeader
        title="二分查找"
        family="二分"
        learningObjectives={[
          '掌握闭区间二分查找中 left 和 right 指针的更新规则',
          '能够根据当前 mid 值和 target 的对比预测下一步搜索区间',
          '理解搜索过程中区间长度单调递减且保持 target 在区间内的不变性'
        ]}
      />

      <div className="main-grid">
        <div className="left-column">
          <InputDisplay
            nums={problemState.nums}
            target={problemState.target}
            answer={problemState.answer}
            showAnswer={showAnswer}
            onGuess={handleGuess}
            addLog={addLog}
          />

          <Visualizer
            nums={problemState.nums}
            target={problemState.target}
            step={step}
            currentStep={currentStep}
            totalSteps={steps.length}
            onPrev={handlePrev}
            onNext={handleNext}
            onReset={handleReset}
            onShowAnswer={handleShowAnswer}
            onHint={handleHint}
            onStepChange={handleStepChange}
            isFirstStep={isFirstStep}
            isLastStep={isLastStep}
            showAnswer={showAnswer}
            hintVisible={hintVisible}
            hintLevel={hintLevel}
          />
        </div>

        <div className="right-column">
          <PredictionPanel
            nums={problemState.nums}
            target={problemState.target}
            step={step}
            currentStep={currentStep}
            addLog={addLog}
            isLastStep={isLastStep}
          />

          <ActivityLog entries={activityLog} />
        </div>
      </div>
    </div>
  );
}
