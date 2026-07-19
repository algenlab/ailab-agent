import React, { useState, useRef, useEffect, useCallback } from 'react';
import TreeView from './components/TreeView';
import StepNavigator from './components/StepNavigator';
import QuizPanel from './components/QuizPanel';
import LogPanel from './components/LogPanel';
import {
  PROBLEM_INPUT,
  FINAL_ANSWER,
  P_TARGET,
  Q_TARGET,
  ALGORITHM_STEPS,
  QUIZ_QUESTIONS,
} from './data';

/* ================================================================
   Helper: format timestamp as HH:MM:SS
   ================================================================ */
function formatTimestamp(date) {
  return date.toTimeString().slice(0, 8);
}

/* ================================================================
   Helper: create a log entry object
   ================================================================ */
let logIdCounter = 0;
function createLogEntry(type, message, iconType) {
  return {
    id: ++logIdCounter,
    timestamp: formatTimestamp(new Date()),
    type,
    message,
    iconType,
  };
}

/* ================================================================
   Main App Component
   ================================================================ */
export default function App() {
  /* ---- Algorithm step state ---- */
  const [stepIndex, setStepIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const autoTimerRef = useRef(null);

  const currentStep = ALGORITHM_STEPS[stepIndex];
  const totalSteps = ALGORITHM_STEPS.length;

  /* ---- Quiz state ---- */
  const [quizState, setQuizState] = useState({});

  /* ---- Activity log ---- */
  const [logEntries, setLogEntries] = useState([
    createLogEntry('start', 'Page loaded. Explore the Binary Tree LCA algorithm!', 'info'),
  ]);

  const addLog = useCallback((type, message, iconType) => {
    setLogEntries((prev) => [...prev, createLogEntry(type, message, iconType)]);
  }, []);

  /* ---- Step navigation handlers ---- */
  const goToStep = useCallback(
    (newIndex) => {
      const clamped = Math.max(0, Math.min(newIndex, totalSteps - 1));
      setStepIndex(clamped);
      if (clamped !== stepIndex) {
        const step = ALGORITHM_STEPS[clamped];
        addLog('navigation', `Navigated to Step ${clamped + 1}: ${step.phase.replace('_', ' ')}`, 'info');
      }
    },
    [stepIndex, totalSteps, addLog]
  );

  const handlePrev = useCallback(() => goToStep(stepIndex - 1), [stepIndex, goToStep]);
  const handleNext = useCallback(() => goToStep(stepIndex + 1), [stepIndex, goToStep]);
  const handleReset = useCallback(() => {
    goToStep(0);
    addLog('navigation', 'Reset to Step 1', 'info');
  }, [goToStep, addLog]);

  /* ---- Auto-play ---- */
  const toggleAutoPlay = useCallback(() => {
    setIsAutoPlaying((prev) => {
      const next = !prev;
      if (next) {
        addLog('navigation', 'Auto-play started', 'info');
      } else {
        addLog('navigation', 'Auto-play stopped', 'info');
      }
      return next;
    });
  }, [addLog]);

  useEffect(() => {
    if (isAutoPlaying) {
      autoTimerRef.current = setInterval(() => {
        setStepIndex((prev) => {
          if (prev >= totalSteps - 1) {
            setIsAutoPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 2200);
    } else {
      if (autoTimerRef.current) clearInterval(autoTimerRef.current);
    }
    return () => {
      if (autoTimerRef.current) clearInterval(autoTimerRef.current);
    };
  }, [isAutoPlaying, totalSteps]);

  // Stop auto-play when user manually navigates
  useEffect(() => {
    if (isAutoPlaying && stepIndex >= totalSteps - 1) {
      setIsAutoPlaying(false);
    }
  }, [stepIndex, isAutoPlaying, totalSteps]);

  /* ---- Quiz handlers ---- */
  const handleSelectOption = useCallback((questionId, optionIndex) => {
    setQuizState((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        selectedIndex: optionIndex,
        answered: false,
        isCorrect: false,
        hintShown: prev[questionId]?.hintShown || false,
        revealed: prev[questionId]?.revealed || false,
      },
    }));
  }, []);

  const handleSubmitAnswer = useCallback(
    (questionId) => {
      const q = QUIZ_QUESTIONS.find((q) => q.id === questionId);
      if (!q) return;
      const state = quizState[questionId] || {};
      const selected = state.selectedIndex;
      const isCorrect = selected === q.correctIndex;

      setQuizState((prev) => ({
        ...prev,
        [questionId]: {
          ...prev[questionId],
          answered: true,
          isCorrect,
        },
      }));

      if (isCorrect) {
        addLog(
          'answer_correct',
          `Q${questionId + 1}: Correctly answered "${q.options[selected]}".`,
          'correct'
        );
      } else {
        addLog(
          'answer_incorrect',
          `Q${questionId + 1}: Incorrectly selected "${q.options[selected]}". Correct answer is "${q.options[q.correctIndex]}".`,
          'incorrect'
        );
      }
    },
    [quizState, addLog]
  );

  const handleShowHint = useCallback(
    (questionId) => {
      setQuizState((prev) => ({
        ...prev,
        [questionId]: {
          ...prev[questionId],
          hintShown: true,
        },
      }));
      addLog('hint', `Q${questionId + 1}: Hint revealed.`, 'hint');
    },
    [addLog]
  );

  const handleRevealAnswer = useCallback(
    (questionId) => {
      const q = QUIZ_QUESTIONS.find((q) => q.id === questionId);
      if (!q) return;
      setQuizState((prev) => ({
        ...prev,
        [questionId]: {
          ...prev[questionId],
          revealed: true,
          answered: true,
          isCorrect: true,
        },
      }));
      addLog(
        'reveal',
        `Q${questionId + 1}: Answer revealed — "${q.options[q.correctIndex]}".`,
        'reveal'
      );
    },
    [addLog]
  );

  /* ---- Render ---- */
  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>Binary Tree Lowest Common Ancestor</h1>
        <p className="subtitle">
          Interactive walkthrough of the DFS-based LCA algorithm on a family lineage tree
        </p>
        <div className="badge-row">
          <span className="badge badge-tree">Tree</span>
          <span className="badge badge-dfs">DFS</span>
          <span className="badge badge-lca">LCA</span>
        </div>
      </header>

      {/* Main content grid */}
      <div className="main-grid">
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Problem display */}
          <div className="card problem-display">
            <div className="card-header">
              <span>📋 Problem Input & Expected Output</span>
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-slate-600)', marginBottom: '0.4rem' }}>
              Input (JSON):
            </div>
            <pre className="input-block">
{`{
  "p": "${P_TARGET}",
  "q": "${Q_TARGET}",
  "tree": {
    "edges": ${JSON.stringify(PROBLEM_INPUT.tree.edges, null, 2)},
    "nodes": ${JSON.stringify(PROBLEM_INPUT.tree.nodes, null, 2)}
  }
}`}
            </pre>
            <div className="answer-block">
              <span>Expected Answer:</span>
              <span className="answer-value">"{FINAL_ANSWER}"</span>
            </div>
          </div>

          {/* Tree visualization */}
          <div className="card">
            <div className="card-header">
              <span>🌳 Tree Visualization</span>
            </div>
            <TreeView
              highlightNodes={currentStep?.highlightNodes || []}
              currentNode={currentStep?.currentNode || null}
              lcaFound={currentStep?.lcaFound || false}
              targetNodes={[P_TARGET, Q_TARGET]}
            />
          </div>

          {/* Activity log */}
          <div className="card">
            <div className="card-header">
              <span>📝 Activity Log</span>
            </div>
            <LogPanel entries={logEntries} />
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Step navigator */}
          <div className="card">
            <div className="card-header">
              <span>🔍 Algorithm Step Visualizer</span>
            </div>
            <StepNavigator
              step={currentStep}
              stepIndex={stepIndex}
              totalSteps={totalSteps}
              onPrev={handlePrev}
              onNext={handleNext}
              onReset={handleReset}
              isAutoPlaying={isAutoPlaying}
              onToggleAuto={toggleAutoPlay}
            />
          </div>

          {/* Checkpoint quiz */}
          <div className="card">
            <div className="card-header">
              <span>✅ Checkpoint Questions</span>
            </div>
            <QuizPanel
              questions={QUIZ_QUESTIONS}
              quizState={quizState}
              onSelectOption={handleSelectOption}
              onSubmitAnswer={handleSubmitAnswer}
              onShowHint={handleShowHint}
              onRevealAnswer={handleRevealAnswer}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
