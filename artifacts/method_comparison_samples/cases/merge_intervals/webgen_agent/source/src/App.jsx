import React, { useState, useCallback, useRef, useEffect } from 'react';
import { problemData, computeSteps, quizQuestions } from './data';
import Visualization from './components/Visualization';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import ProblemInfo from './components/ProblemInfo';

function getTimeStr() {
  const d = new Date();
  return (
    String(d.getHours()).padStart(2, '0') +
    ':' +
    String(d.getMinutes()).padStart(2, '0') +
    ':' +
    String(d.getSeconds()).padStart(2, '0')
  );
}

export default function App() {
  const { steps, sorted } = computeSteps(problemData.input.intervals);
  const [currentStep, setCurrentStep] = useState(0);
  const [logs, setLogs] = useState([
    { time: getTimeStr(), icon: '🚀', msg: '页面加载完成，准备开始学习合并区间算法。' },
  ]);
  const [quizState, setQuizState] = useState({});
  // quizState: { [qid]: { selected: key, status: 'correct'|'wrong'|null, revealed: bool } }

  const addLog = useCallback((icon, msg) => {
    setLogs((prev) => [{ time: getTimeStr(), icon, msg }, ...prev.slice(0, 49)]);
  }, []);

  const totalSteps = steps.length;
  const stepData = steps[currentStep];

  const handleNext = useCallback(() => {
    setCurrentStep((p) => {
      const next = Math.min(p + 1, totalSteps - 1);
      addLog('▶️', `跳转到步骤 ${next + 1}/${totalSteps}`);
      return next;
    });
  }, [totalSteps, addLog]);

  const handlePrev = useCallback(() => {
    setCurrentStep((p) => {
      const prev = Math.max(p - 1, 0);
      addLog('⏪', `返回步骤 ${prev + 1}/${totalSteps}`);
      return prev;
    });
  }, [addLog]);

  const handleReset = useCallback(() => {
    setCurrentStep(0);
    addLog('🔄', '重置可视化到初始状态。');
  }, [addLog]);

  const handleJumpToEnd = useCallback(() => {
    setCurrentStep(totalSteps - 1);
    addLog('⏩', '跳转到最终结果。');
  }, [totalSteps, addLog]);

  const handleQuizAnswer = useCallback(
    (qid, key, correctKey, explanation) => {
      setQuizState((prev) => {
        const current = prev[qid] || {};
        if (current.revealed) return prev; // already revealed
        const isCorrect = key === correctKey;
        return {
          ...prev,
          [qid]: { selected: key, status: isCorrect ? 'correct' : 'wrong', revealed: false },
        };
      });
      const isCorrect = key === correctKey;
      addLog(
        isCorrect ? '✅' : '❌',
        isCorrect
          ? `问题回答正确！${explanation}`
          : `回答错误。${explanation}`
      );
    },
    [addLog]
  );

  const handleShowAnswer = useCallback(
    (qid, correctKey, explanation) => {
      setQuizState((prev) => ({
        ...prev,
        [qid]: { selected: correctKey, status: 'correct', revealed: true },
      }));
      addLog('💡', `查看答案：${explanation}`);
    },
    [addLog]
  );

  const handleHint = useCallback(
    (qid, hintText) => {
      addLog('🔍', `提示：${hintText}`);
    },
    [addLog]
  );

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <h1>{problemData.title}</h1>
        <span className="badge">算法族：{problemData.family}</span>
      </header>

      <div className="grid-main">
        {/* Left Column: Problem + Quiz */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ProblemInfo
            input={problemData.input}
            expectedOutput={problemData.expectedOutput}
            description={problemData.description}
            objectives={problemData.objectives}
            strategy={problemData.referenceStrategy}
          />
          <QuizPanel
            questions={quizQuestions}
            quizState={quizState}
            onAnswer={handleQuizAnswer}
            onShowAnswer={handleShowAnswer}
            onHint={handleHint}
          />
        </div>

        {/* Right Column: Visualization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Visualization
            stepData={stepData}
            currentStep={currentStep}
            totalSteps={totalSteps}
            onNext={handleNext}
            onPrev={handlePrev}
            onReset={handleReset}
            onJumpToEnd={handleJumpToEnd}
            sortedIntervals={sorted}
            expectedOutput={problemData.expectedOutput}
          />
        </div>

        {/* Activity Log: full width */}
        <ActivityLog logs={logs} />
      </div>

      <footer className="app-footer">
        合并区间 · 贪心算法交互教学 · 所有数据在本地处理
      </footer>
    </div>
  );
}
