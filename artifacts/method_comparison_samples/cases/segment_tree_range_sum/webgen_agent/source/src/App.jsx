import React, { useState, useCallback, useRef, useEffect } from 'react';
import ProblemDisplay from './components/ProblemDisplay';
import SegmentTreeCanvas from './components/SegmentTreeCanvas';
import StepNavigator from './components/StepNavigator';
import LearnerQuestions from './components/LearnerQuestions';
import ActivityLog from './components/ActivityLog';
import { STEPS, PROBLEM_DATA, INITIAL_STATE, FINAL_ANSWER } from './data/algorithmData';
import './App.css';

export default function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [logEntries, setLogEntries] = useState([]);
  const [revealedAnswers, setRevealedAnswers] = useState(new Set());
  const [questionStates, setQuestionStates] = useState({});
  const [highlightNodes, setHighlightNodes] = useState([]);
  const [segmentTreeSnapshot, setSegmentTreeSnapshot] = useState(null);
  const logIdRef = useRef(0);

  const addLog = useCallback((message, type = 'info') => {
    const id = ++logIdRef.current;
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    setLogEntries(prev => [...prev.slice(-49), { id, timestamp, message, type }]);
  }, []);

  const step = STEPS[currentStep];
  const isLastStep = currentStep === STEPS.length - 1;
  const isFirstStep = currentStep === 0;

  const goToStep = useCallback((index) => {
    if (index >= 0 && index < STEPS.length) {
      setCurrentStep(index);
      const s = STEPS[index];
      setHighlightNodes(s.highlightNodes || []);
      setSegmentTreeSnapshot(s.treeSnapshot || null);
      addLog(`进入步骤 ${index + 1}: ${s.title}`, 'step');
    }
  }, [addLog]);

  const goNext = useCallback(() => {
    if (!isLastStep) goToStep(currentStep + 1);
  }, [currentStep, isLastStep, goToStep]);

  const goPrev = useCallback(() => {
    if (!isFirstStep) goToStep(currentStep - 1);
  }, [currentStep, isFirstStep, goToStep]);

  const handleQuestionSubmit = useCallback((qId, correct, learnerAnswer) => {
    setQuestionStates(prev => ({ ...prev, [qId]: { correct, learnerAnswer } }));
    if (correct) {
      addLog(`✅ 问题 ${qId}: 回答正确！答案: ${learnerAnswer}`, 'success');
    } else {
      addLog(`❌ 问题 ${qId}: 回答不正确。你的答案: ${learnerAnswer}`, 'error');
    }
  }, [addLog]);

  const handleShowHint = useCallback((qId, hint) => {
    addLog(`💡 问题 ${qId}: 查看提示 - "${hint}"`, 'hint');
  }, [addLog]);

  const handleShowAnswer = useCallback((qId, answer) => {
    setRevealedAnswers(prev => new Set([...prev, qId]));
    addLog(`🔑 问题 ${qId}: 显示答案 - "${answer}"`, 'answer');
  }, [addLog]);

  useEffect(() => {
    const s = STEPS[0];
    if (s) {
      setHighlightNodes(s.highlightNodes || []);
      setSegmentTreeSnapshot(s.treeSnapshot || null);
    }
    addLog('📚 欢迎来到线段树区间和学习！请浏览步骤了解算法。', 'info');
  }, []);

  useEffect(() => {
    const s = STEPS[currentStep];
    if (s) {
      setHighlightNodes(s.highlightNodes || []);
      setSegmentTreeSnapshot(s.treeSnapshot || null);
    }
  }, [currentStep]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>线段树区间和</h1>
          <span className="algorithm-badge">区间结构</span>
        </div>
        <p className="header-subtitle">物流中心包裹重量查询与修正 — 交互式算法可视化</p>
      </header>

      <div className="app-body">
        <main className="main-content">
          <section className="card problem-card">
            <h2>📋 题目信息</h2>
            <ProblemDisplay
              nums={PROBLEM_DATA.nums}
              query={PROBLEM_DATA.query}
              update={PROBLEM_DATA.update}
              finalAnswer={FINAL_ANSWER}
            />
          </section>

          <section className="card vis-card">
            <h2>🌳 线段树可视化</h2>
            <SegmentTreeCanvas
              highlightNodes={highlightNodes}
              treeSnapshot={segmentTreeSnapshot}
              stepIndex={currentStep}
              stepTitle={step?.title || ''}
            />
          </section>

          <section className="card steps-card">
            <h2>🔄 算法步骤</h2>
            <StepNavigator
              steps={STEPS}
              currentStep={currentStep}
              onGoToStep={goToStep}
              onNext={goNext}
              onPrev={goPrev}
              isFirstStep={isFirstStep}
              isLastStep={isLastStep}
            />
          </section>

          <section className="card questions-card">
            <h2>✏️ 学习检测</h2>
            <LearnerQuestions
              questionStates={questionStates}
              onQuestionSubmit={handleQuestionSubmit}
              onShowHint={handleShowHint}
              onShowAnswer={handleShowAnswer}
              revealedAnswers={revealedAnswers}
            />
          </section>
        </main>

        <aside className="sidebar">
          <ActivityLog entries={logEntries} />
        </aside>
      </div>
    </div>
  );
}
