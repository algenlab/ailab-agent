import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { generateTrace, PROBLEM_INPUT, EXPECTED_OUTPUT } from './traceGenerator';
import { checkpoints } from './checkpointData';

// ==================== Helpers ====================

function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function renderArray(arr) {
  return `[${arr.join(', ')}]`;
}

// ==================== Learning Log Entry ====================

function LogEntry({ icon, message, time }) {
  return (
    <div className="log-entry">
      <span className="log-time">{time}</span>
      <span className="log-icon">{icon}</span>
      <span className="log-message">{message}</span>
    </div>
  );
}

// ==================== Array Cell ====================

function ArrayCell({ value, state }) {
  const className = `array-cell ${state}`;
  return <span className={className}>{value}</span>;
}

// ==================== Checkpoint Component ====================

function CheckpointItem({ checkpoint, index, onLog }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [isCorrect, setIsCorrect] = useState(null);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);

  const handleSelect = (optIndex) => {
    if (submitted) return;
    setSelectedOption(optIndex);
  };

  const handleSubmit = () => {
    if (selectedOption === null || submitted) return;
    const correct = selectedOption === checkpoint.correctIndex;
    setIsCorrect(correct);
    setSubmitted(true);
    onLog(
      correct ? '\u2705' : '\u274C',
      `Checkpoint ${checkpoint.id}: ${correct ? 'Correct' : 'Incorrect'} - "${checkpoint.question.slice(0, 50)}..."`
    );
  };

  const handleHint = () => {
    setShowHint(!showHint);
    if (!showHint) {
      onLog('\uD83D\uDCA1', `Hint requested for checkpoint ${checkpoint.id}`);
    }
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    setShowExplanation(true);
    setSelectedOption(checkpoint.correctIndex);
    setSubmitted(true);
    if (isCorrect === null) {
      setIsCorrect(true);
      onLog('\uD83D\uDC41\uFE0F', `Answer revealed for checkpoint ${checkpoint.id}`);
    }
  };

  const containerClass = [
    'checkpoint-item',
    submitted && isCorrect === true ? 'answered-correct' : '',
    submitted && isCorrect === false ? 'answered-incorrect' : ''
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={containerClass}>
      <h4>
        <strong>Checkpoint {checkpoint.id}:</strong> {checkpoint.question}
      </h4>

      <div className="checkpoint-options">
        {checkpoint.options.map((opt, oi) => {
          let optClass = 'option-btn';
          if (selectedOption === oi) optClass += ' selected';
          if (showAnswer && oi === checkpoint.correctIndex) optClass += ' correct-reveal';
          if (submitted && selectedOption === oi && !isCorrect) optClass += ' incorrect-reveal';
          return (
            <button
              key={oi}
              className={optClass}
              onClick={() => handleSelect(oi)}
              disabled={submitted}
              aria-label={`Option ${String.fromCharCode(65 + oi)}: ${opt}`}
            >
              <strong>{String.fromCharCode(65 + oi)}.</strong> {opt}
            </button>
          );
        })}
      </div>

      <div className="checkpoint-actions">
        <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={selectedOption === null || submitted}>
          Check Answer
        </button>
        <button className="btn btn-sm" onClick={handleHint}>
          {showHint ? 'Hide Hint' : '\uD83D\uDCA1 Hint'}
        </button>
        <button className="btn btn-warning btn-sm" onClick={handleShowAnswer} disabled={submitted && isCorrect === true && showAnswer}>
          \uD83D\uDC41 Show Answer
        </button>
      </div>

      {showHint && <div className="hint-box fade-in">{checkpoint.hint}</div>}

      {submitted && isCorrect === true && !showAnswer && (
        <div className="feedback-msg correct fade-in">{checkpoint.feedbackCorrect}</div>
      )}

      {submitted && isCorrect === false && (
        <div className="feedback-msg incorrect fade-in">{checkpoint.feedbackIncorrect}</div>
      )}

      {showExplanation && (
        <div className="explanation-box fade-in">
          <strong>Explanation:</strong> {checkpoint.answerExplanation}
        </div>
      )}
    </div>
  );
}

// ==================== Main App ====================

export default function App() {
  const trace = useMemo(() => generateTrace(PROBLEM_INPUT), []);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [logs, setLogs] = useState([]);
  const playIntervalRef = useRef(null);
  const logContainerRef = useRef(null);

  const step = trace[currentStep];
  const totalSteps = trace.length;

  // Auto-scroll log
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Auto-play
  useEffect(() => {
    if (isPlaying) {
      playIntervalRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= totalSteps - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 900);
    } else {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    }
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, totalSteps]);

  const addLog = useCallback((icon, message) => {
    setLogs((prev) => [...prev, { icon, message, time: formatTime(), id: Date.now() + Math.random() }]);
  }, []);

  // Navigation handlers
  const goToStep = useCallback(
    (target) => {
      const clamped = Math.max(0, Math.min(totalSteps - 1, target));
      setCurrentStep(clamped);
      setIsPlaying(false);
      if (clamped !== currentStep) {
        addLog('\uD83D\uDCCD', `Navigated to step ${clamped + 1} of ${totalSteps} (${trace[clamped].type})`);
      }
    },
    [totalSteps, currentStep, addLog, trace]
  );

  const goNext = useCallback(() => goToStep(currentStep + 1), [goToStep, currentStep]);
  const goPrev = useCallback(() => goToStep(currentStep - 1), [goToStep, currentStep]);
  const goReset = useCallback(() => {
    goToStep(0);
    addLog('\uD83D\uDD04', 'Reset visualization to beginning');
  }, [goToStep, addLog]);

  const togglePlay = useCallback(() => {
    const next = !isPlaying;
    setIsPlaying(next);
    if (next && currentStep >= totalSteps - 1) {
      setCurrentStep(0);
    }
    addLog(next ? '\u25B6\uFE0F' : '\u23F8\uFE0F', next ? 'Started auto-play' : 'Paused auto-play');
  }, [isPlaying, currentStep, totalSteps, addLog]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e) => {
      if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
      if (e.key === 'ArrowRight') goNext();
      else if (e.key === 'ArrowLeft') goPrev();
      else if (e.key === ' ') { e.preventDefault(); togglePlay(); }
      else if (e.key === 'r' || e.key === 'R') goReset();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [goNext, goPrev, togglePlay, goReset]);

  // Progress percentage
  const progressPct = totalSteps > 1 ? ((currentStep / (totalSteps - 1)) * 100).toFixed(1) : 0;

  // Determine if this step has a new result
  const lastResultIndex =
    step.type === 'complete' ? step.results.length - 1 : -1;

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <h1>Permutations</h1>
        <p className="subtitle">Algorithm Family: Backtracking / Recursion</p>
      </header>

      {/* Problem Statement */}
      <section className="card" aria-label="Problem statement">
        <div className="card-header">
          <h2>Problem Statement</h2>
          <span className="badge">Backtracking</span>
        </div>
        <p style={{ fontSize: '0.9rem', lineHeight: 1.7, color: 'var(--color-text-secondary)' }}>
          You are a security expert facing a combination lock composed of a set of non-repeating numbers
          (input array <code>nums</code>). You need to generate all possible unlocking number sequences
          (i.e., all permutations of <code>nums</code>) in order to try them systematically.
          Please output a list of all permutations.
        </p>
      </section>

      {/* Input / Output */}
      <section className="card" aria-label="Concrete input and expected output">
        <div className="card-header">
          <h2>Concrete Input & Expected Output</h2>
        </div>
        <div className="io-grid">
          <div className="io-block">
            <h3>Input (JSON)</h3>
            <div className="io-value">{JSON.stringify({ nums: PROBLEM_INPUT }, null, 2)}</div>
          </div>
          <div className="io-block">
            <h3>Expected Final Answer (JSON)</h3>
            <div className="io-value">{JSON.stringify(EXPECTED_OUTPUT, null, 2)}</div>
          </div>
        </div>
      </section>

      {/* Visualization */}
      <section className="card" aria-label="Algorithm visualization">
        <div className="card-header">
          <h2>Step-by-Step Visualization</h2>
          <span className="badge">
            Step {currentStep + 1} of {totalSteps}
          </span>
        </div>

        {/* Progress bar */}
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
        </div>

        <div className="viz-layout">
          {/* Left: state display */}
          <div className="viz-panel">
            <div className="state-row">
              <div className="state-block" style={{ flex: '1 1 auto' }}>
                <h4>Path (current choices)</h4>
                <div className="path-array">
                  {step.path.length === 0 ? (
                    <span className="empty-path">empty</span>
                  ) : (
                    step.path.map((val, i) => (
                      <ArrayCell key={i} value={val} state="path-cell" />
                    ))
                  )}
                </div>
              </div>
              <div className="state-block">
                <h4>Depth</h4>
                <div className="state-value">{step.depth}</div>
              </div>
            </div>

            <div className="state-row">
              <div className="state-block" style={{ flex: '1 1 auto' }}>
                <h4>Used Array</h4>
                <div className="array-display">
                  {step.used.map((isUsed, i) => (
                    <ArrayCell
                      key={i}
                      value={PROBLEM_INPUT[i]}
                      state={isUsed ? 'used-true' : 'used-false'}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Step description */}
            <div className={`step-description type-${step.type} fade-in`} key={currentStep}>
              {step.description}
            </div>

            {/* Accumulated results */}
            {step.results.length > 0 && (
              <div className="results-display">
                <h4>Results Found ({step.results.length} of {EXPECTED_OUTPUT.length})</h4>
                <div className="results-grid">
                  {step.results.map((perm, i) => (
                    <span
                      key={i}
                      className={`result-perm${i === lastResultIndex ? ' newest' : ''}`}
                    >
                      {renderArray(perm)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: final answer reference */}
          <div className="viz-panel">
            <div className="final-answer-section">
              <h4>Target: All 6 Permutations</h4>
              <div className="final-perms">
                {EXPECTED_OUTPUT.map((perm, i) => (
                  <span key={i} className="final-perm-tag">
                    {renderArray(perm)}
                  </span>
                ))}
              </div>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '10px', lineHeight: 1.5 }}>
              <strong>Reference Strategy:</strong> Use <code>path</code> to save the current choices,
              recursively select unused numbers, and undo the selection upon return (backtrack).
            </p>
          </div>
        </div>

        {/* Navigation Controls */}
        <div className="nav-controls" role="toolbar" aria-label="Step navigation">
          <button className="btn btn-sm" onClick={goReset} disabled={currentStep === 0} aria-label="Reset to start">
            \u23EE First
          </button>
          <button className="btn btn-icon" onClick={goPrev} disabled={currentStep === 0} aria-label="Previous step">
            \u25C0
          </button>
          <button
            className={`btn ${isPlaying ? 'btn-warning' : 'btn-primary'}`}
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pause auto-play' : 'Start auto-play'}
          >
            {isPlaying ? '\u23F8 Pause' : '\u25B6 Play'}
          </button>
          <button
            className="btn btn-icon"
            onClick={goNext}
            disabled={currentStep >= totalSteps - 1}
            aria-label="Next step"
          >
            \u25B6
          </button>
          <button
            className="btn btn-sm"
            onClick={() => goToStep(totalSteps - 1)}
            disabled={currentStep >= totalSteps - 1}
            aria-label="Skip to end"
          >
            Last \u23ED
          </button>
          <span className="step-counter">
            {currentStep + 1} / {totalSteps}
          </span>
        </div>

        <p style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
          Keyboard shortcuts: <kbd>\u2190</kbd> previous step, <kbd>\u2192</kbd> next step, <kbd>Space</kbd> play/pause, <kbd>R</kbd> reset
        </p>
      </section>

      {/* Checkpoint Questions */}
      <section className="card" aria-label="Checkpoint questions">
        <div className="card-header">
          <h2>Checkpoint Questions</h2>
          <span className="badge">Test Your Understanding</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '14px' }}>
          Answer these questions to check your understanding of the backtracking algorithm.
          Select an option and click "Check Answer" for feedback.
        </p>
        {checkpoints.map((cp, idx) => (
          <CheckpointItem key={cp.id} checkpoint={cp} index={idx} onLog={addLog} />
        ))}
      </section>

      {/* Learning Log */}
      <section className="card" aria-label="Learning activity log">
        <div className="card-header">
          <h2>Learning Activity Log</h2>
          <span className="badge">{logs.length} entries</span>
        </div>
        <div className="log-container" ref={logContainerRef}>
          {logs.length === 0 ? (
            <div className="log-empty">No activities recorded yet. Interact with the visualization or checkpoint questions to populate the log.</div>
          ) : (
            logs.map((entry) => (
              <LogEntry key={entry.id} icon={entry.icon} message={entry.message} time={entry.time} />
            ))
          )}
        </div>
      </section>
    </div>
  );
}