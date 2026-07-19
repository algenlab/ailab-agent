import React, { useState, useCallback, useRef, useEffect } from 'react';
import { generateSteps } from './utils/generateSteps';
import InputOutput from './components/InputOutput';
import StateVisualizer from './components/StateVisualizer';
import NavigationControls from './components/NavigationControls';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';

const INPUT_NUMS = [1, 2, 3];
const FINAL_ANSWER = [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]];

export default function App() {
  // Pre-compute all steps once
  const stepsRef = useRef(null);
  if (!stepsRef.current) {
    stepsRef.current = generateSteps(INPUT_NUMS);
  }
  const steps = stepsRef.current;

  const [currentStep, setCurrentStep] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [speed, setSpeed] = useState(800);
  const [activityLog, setActivityLog] = useState([]);
  const [prevResultLen, setPrevResultLen] = useState(0);
  const autoPlayTimerRef = useRef(null);

  // Determine if the current step just completed a new permutation
  const step = steps[currentStep];
  const isNewResult = step && step.action === 'complete';

  // Reset prevResultLen when step changes
  useEffect(() => {
    if (step && step.action !== 'complete') {
      setPrevResultLen(step.result.length);
    } else if (step && step.action === 'complete') {
      setPrevResultLen(step.result.length - 1);
    }
  }, [currentStep]);

  // Add log entry helper
  const addLogEntry = useCallback((entry) => {
    setActivityLog((prev) => [...prev, { ...entry, id: Date.now() + Math.random() }]);
  }, []);

  // Log navigation
  const logNav = useCallback(
    (action, from, to) => {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      addLogEntry({
        time: timeStr,
        type: 'nav',
        message: action === 'reset'
          ? `重置到步骤 1`
          : action === 'auto-start'
            ? `自动播放开始（速度 ${speed}ms）`
            : action === 'auto-stop'
              ? '自动播放停止'
              : `从步骤 ${from + 1} 跳转到步骤 ${to + 1}`,
      });
    },
    [addLogEntry, speed]
  );

  // Auto-play logic
  useEffect(() => {
    if (isAutoPlaying) {
      autoPlayTimerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= steps.length - 1) {
            setIsAutoPlaying(false);
            logNav('auto-stop', prev, prev);
            return prev;
          }
          return prev + 1;
        });
      }, speed);
    } else {
      if (autoPlayTimerRef.current) {
        clearInterval(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    }
    return () => {
      if (autoPlayTimerRef.current) {
        clearInterval(autoPlayTimerRef.current);
      }
    };
  }, [isAutoPlaying, speed, steps.length, logNav]);

  // Navigation handlers
  const handleStepPrev = useCallback(() => {
    setCurrentStep((prev) => {
      const next = Math.max(0, prev - 1);
      logNav('step', prev, next);
      return next;
    });
  }, [logNav]);

  const handleStepNext = useCallback(() => {
    setCurrentStep((prev) => {
      const next = Math.min(steps.length - 1, prev + 1);
      logNav('step', prev, next);
      if (next >= steps.length - 1) {
        setIsAutoPlaying(false);
      }
      return next;
    });
  }, [steps.length, logNav]);

  const handleReset = useCallback(() => {
    setCurrentStep((prev) => {
      logNav('reset', prev, 0);
      return 0;
    });
    setIsAutoPlaying(false);
  }, [logNav]);

  const handleToggleAutoPlay = useCallback(() => {
    setIsAutoPlaying((prev) => {
      const next = !prev;
      if (next) {
        logNav('auto-start', currentStep, currentStep);
        // If at end, restart
        if (currentStep >= steps.length - 1) {
          setCurrentStep(0);
        }
      } else {
        logNav('auto-stop', currentStep, currentStep);
      }
      return next;
    });
  }, [currentStep, steps.length, logNav]);

  const handleSpeedChange = useCallback((newSpeed) => {
    setSpeed(newSpeed);
    addLogEntry({
      time: new Date().toTimeString().slice(0, 8),
      type: 'info',
      message: `播放速度调整为 ${newSpeed}ms`,
    });
  }, [addLogEntry]);

  const handleQuizLogEntry = useCallback(
    (entry) => {
      addLogEntry(entry);
    },
    [addLogEntry]
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔐 全排列 — 密码锁破解</h1>
        <p className="subtitle">回溯 / 递归算法 · 交互式可视化学习</p>
        <div className="badge-row">
          <span className="badge badge-primary">回溯算法</span>
          <span className="badge badge-warning">递归</span>
          <span className="badge badge-primary">状态空间搜索</span>
        </div>
      </header>

      <div className="app-grid">
        <InputOutput nums={INPUT_NUMS} answer={FINAL_ANSWER} />

        <StateVisualizer
          step={step}
          nums={INPUT_NUMS}
          isNewResult={isNewResult}
        />

        <NavigationControls
          currentStep={currentStep}
          totalSteps={steps.length}
          isAutoPlaying={isAutoPlaying}
          speed={speed}
          onStepPrev={handleStepPrev}
          onStepNext={handleStepNext}
          onReset={handleReset}
          onToggleAutoPlay={handleToggleAutoPlay}
          onSpeedChange={handleSpeedChange}
        />

        <QuizPanel onLogEntry={handleQuizLogEntry} />

        <ActivityLog entries={activityLog} />
      </div>
    </div>
  );
}
