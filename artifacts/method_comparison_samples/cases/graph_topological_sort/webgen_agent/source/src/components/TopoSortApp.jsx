import React, { useState, useCallback, useRef, useEffect } from 'react';
import { ProblemCard } from './ProblemCard';
import { StrategyCard } from './StrategyCard';
import { VizPanel } from './VizPanel';
import { QuizPanel } from './QuizPanel';
import { ActivityLog } from './ActivityLog';
import { useTopoSort } from '../useTopoSort';
import { useActivityLog } from '../useActivityLog';
import { QUESTIONS } from '../data';

export function TopoSortApp() {
  const { state, steps, stepIndex, goNext, goPrev, goReset, isDone } = useTopoSort();
  const { entries, log } = useActivityLog();

  const [activeQuiz, setActiveQuiz] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizFeedback, setQuizFeedback] = useState({});
  const [showHints, setShowHints] = useState({});
  const [showAnswers, setShowAnswers] = useState({});

  const handleQuizSelect = useCallback((qIdx, optionIdx) => {
    if (quizFeedback[qIdx] !== undefined) return;
    const q = QUESTIONS[qIdx];
    const chosen = q.options[optionIdx];
    const isCorrect = chosen === q.answer;
    setQuizAnswers(prev => ({ ...prev, [qIdx]: optionIdx }));
    setQuizFeedback(prev => ({ ...prev, [qIdx]: isCorrect ? 'correct' : 'incorrect' }));
    log(isCorrect ? 'correct' : 'incorrect',
      isCorrect
        ? `✅ Q${qIdx + 1}: 正确！你选择了 "${chosen}"。`
        : `❌ Q${qIdx + 1}: 不对。你选择了 "${chosen}"，正确答案是 "${q.answer}"。`
    );
  }, [quizFeedback, log]);

  const handleHint = useCallback((qIdx) => {
    setShowHints(prev => ({ ...prev, [qIdx]: true }));
    log('hint', `💡 Q${qIdx + 1}: 提示 - ${QUESTIONS[qIdx].hint}`);
  }, [log]);

  const handleShowAnswer = useCallback((qIdx) => {
    setShowAnswers(prev => ({ ...prev, [qIdx]: true }));
    log('info', `📖 Q${qIdx + 1}: 显示答案 - "${QUESTIONS[qIdx].answer}"`);
  }, [log]);

  const handleStepAction = useCallback((action) => {
    if (action === 'next') goNext();
    else if (action === 'prev') goPrev();
    else if (action === 'reset') goReset();
    log('info', `🔧 步骤操作: ${action === 'next' ? '下一步' : action === 'prev' ? '上一步' : '重置'}`);
  }, [goNext, goPrev, goReset, log]);

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <h1>拓扑排序</h1>
        <span className="badge">BFS/DFS 基础图</span>
        <span className="badge">Kahn 算法</span>
        <p style={{ marginTop: 8, opacity: 0.9, fontSize: '0.9rem' }}>
          你正在为教务系统开发选课推荐功能。给定课程依赖图，请返回一个合法的选课顺序列表。
        </p>
      </div>

      {/* Main grid */}
      <div className="main-grid">
        <ProblemCard />
        <StrategyCard />
      </div>

      {/* Visualization */}
      <VizPanel
        state={state}
        stepIndex={stepIndex}
        totalSteps={steps.length}
        isDone={isDone}
        onPrev={() => handleStepAction('prev')}
        onNext={() => handleStepAction('next')}
        onReset={() => handleStepAction('reset')}
      />

      {/* Quiz panel */}
      <QuizPanel
        activeQuiz={activeQuiz}
        setActiveQuiz={setActiveQuiz}
        quizAnswers={quizAnswers}
        quizFeedback={quizFeedback}
        showHints={showHints}
        showAnswers={showAnswers}
        onSelect={handleQuizSelect}
        onHint={handleHint}
        onShowAnswer={handleShowAnswer}
      />

      {/* Activity Log */}
      <ActivityLog entries={entries} />
    </div>
  );
}
