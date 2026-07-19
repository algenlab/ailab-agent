import React, { useState, useCallback, useRef, useEffect } from 'react';
import ProblemDisplay from './components/ProblemDisplay';
import UnionFindVisualizer from './components/UnionFindVisualizer';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import { useUnionFind } from './hooks/useUnionFind';
import './App.css';

const INPUT_DATA = {
  isConnected: [
    [1, 1, 0],
    [1, 1, 0],
    [0, 0, 1]
  ]
};

const EXPECTED_ANSWER = 2;

export default function App() {
  const [logEntries, setLogEntries] = useState([]);
  const [quizAttempts, setQuizAttempts] = useState({});
  const logIdRef = useRef(0);

  const addLog = useCallback((message, type = 'info') => {
    const id = ++logIdRef.current;
    setLogEntries(prev => [...prev.slice(-49), { id, message, type, timestamp: Date.now() }]);
  }, []);

  const ufState = useUnionFind(INPUT_DATA.isConnected, addLog);

  const handleQuizAttempt = useCallback((questionId, isCorrect) => {
    setQuizAttempts(prev => ({ ...prev, [questionId]: isCorrect }));
    addLog(
      isCorrect
        ? `✅ 问题 ${questionId}：回答正确！`
        : `❌ 问题 ${questionId}：回答错误，请再试一次。`,
      isCorrect ? 'success' : 'error'
    );
  }, [addLog]);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">
          <span className="title-icon">🌐</span>
          省份数量
          <span className="title-badge">并查集</span>
        </h1>
        <p className="app-subtitle">交互式算法学习页面</p>
      </header>

      <div className="app-content">
        <div className="main-column">
          <ProblemDisplay
            input={INPUT_DATA}
            expectedAnswer={EXPECTED_ANSWER}
          />
          <UnionFindVisualizer ufState={ufState} input={INPUT_DATA} />
        </div>

        <div className="side-column">
          <QuizPanel
            ufState={ufState}
            input={INPUT_DATA}
            expectedAnswer={EXPECTED_ANSWER}
            onAttempt={handleQuizAttempt}
            attempts={quizAttempts}
          />
          <ActivityLog entries={logEntries} />
        </div>
      </div>

      <footer className="app-footer">
        <p>并查集（Union-Find）算法 · 省份数量问题</p>
      </footer>
    </div>
  );
}