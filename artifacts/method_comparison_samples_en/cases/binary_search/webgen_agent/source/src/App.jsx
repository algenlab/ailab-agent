import React, { useState, useCallback } from 'react';
import ProblemDisplay from './components/ProblemDisplay';
import AlgorithmVisualizer from './components/AlgorithmVisualizer';
import CheckpointPanel from './components/CheckpointPanel';
import LearningLog from './components/LearningLog';

const PROBLEM_DATA = {
  nums: [-1, 0, 3, 5, 9, 12],
  target: 9,
};

const FINAL_ANSWER = 4;

export default function App() {
  const [logEntries, setLogEntries] = useState([]);

  const addLogEntry = useCallback((action, detail) => {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour12: false });
    setLogEntries((prev) => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        time,
        action,
        detail,
      },
    ]);
  }, []);

  return (
    <div>
      <header className="header">
        <div className="header-content">
          <h1>Binary Search</h1>
          <span className="badge">Binary</span>
        </div>
      </header>

      <div className="container">
        {/* Problem description */}
        <section className="section">
          <h2 className="section-title">
            <span className="icon" role="img" aria-label="book">📚</span>
            Problem Statement
          </h2>
          <p style={{ marginBottom: '12px' }}>
            You work in a library where books with unique call numbers are arranged in order on shelves.
            Given a shelf array <span className="inline-code">nums</span> (each position <span className="inline-code">i</span> stores call number <span className="inline-code">nums[i]</span>),
            and a target call number needed by a reader, return the index of target, or -1 if it does not exist.
          </p>

          <div className="strategy-box">
            <strong>Strategy:</strong> Maintain a closed interval and discard half after comparing the midpoint each time.
          </div>
        </section>

        {/* Learning Objectives */}
        <section className="section">
          <h2 className="section-title">
            <span className="icon" role="img" aria-label="target">🎯</span>
            Learning Objectives
          </h2>
          <ul className="objectives-list">
            <li>Master the update rules for left and right pointers in closed-interval binary search.</li>
            <li>Be able to predict the next search interval based on the comparison between the current mid value and target.</li>
            <li>Understand that the interval length strictly decreases while the invariant that target remains within the interval is maintained.</li>
          </ul>
        </section>

        {/* Input / Output */}
        <ProblemDisplay nums={PROBLEM_DATA.nums} target={PROBLEM_DATA.target} finalAnswer={FINAL_ANSWER} />

        {/* Algorithm Visualization */}
        <AlgorithmVisualizer
          nums={PROBLEM_DATA.nums}
          target={PROBLEM_DATA.target}
          finalAnswer={FINAL_ANSWER}
          addLogEntry={addLogEntry}
        />

        {/* Checkpoint */}
        <CheckpointPanel
          nums={PROBLEM_DATA.nums}
          target={PROBLEM_DATA.target}
          addLogEntry={addLogEntry}
        />

        {/* Learning Log */}
        <section className="section">
          <h2 className="section-title">
            <span className="icon" role="img" aria-label="log">📋</span>
            Learning Activity Log
          </h2>
          <LearningLog entries={logEntries} />
        </section>
      </div>
    </div>
  );
}
