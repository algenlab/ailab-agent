import React, { useState, useCallback, useRef, useEffect } from 'react';
import { problemInput, expectedAnswer, learningObjectives, steps, checkpoints } from './algorithmData';

// --- Utility ---
function formatInterval(interval) {
  return '[' + interval.join(', ') + ']';
}

function formatMerged(merged) {
  return '[' + merged.map((iv) => '[' + iv.join(', ') + ']').join(', ') + ']';
}

// Compact JSON formatting: small arrays stay on one line
function toCompactJSON(obj, indent = 0) {
  const prefix = ' '.repeat(indent);
  const childPrefix = ' '.repeat(indent + 2);

  if (obj === null || obj === undefined) return 'null';
  if (typeof obj === 'boolean') return obj ? 'true' : 'false';
  if (typeof obj === 'number') return String(obj);
  if (typeof obj === 'string') return JSON.stringify(obj);

  if (Array.isArray(obj)) {
    if (obj.length === 0) return '[]';
    // If all items are primitive or small arrays of primitives, keep inline
    const allSimple = obj.every((item) => {
      if (Array.isArray(item)) {
        return item.length <= 4 && item.every((el) => typeof el === 'number' || typeof el === 'string');
      }
      return typeof item === 'number' || typeof item === 'string' || typeof item === 'boolean';
    });
    if (allSimple) {
      // For nested arrays like intervals
      const hasNestedArrays = obj.some((item) => Array.isArray(item));
      if (hasNestedArrays && obj.length <= 6) {
        // Pretty print: top-level items each on their own line, inner arrays compact
        const items = obj.map((item, i) => {
          const comma = i < obj.length - 1 ? ',' : '';
          return childPrefix + toCompactJSON(item, indent + 2) + comma;
        }).join('\n');
        return '[\n' + items + '\n' + prefix + ']';
      }
      // Fully inline
      return '[' + obj.map((item) => toCompactJSON(item, indent)).join(', ') + ']';
    }
    // General array handling
    const items = obj.map((item, i) => {
      const comma = i < obj.length - 1 ? ',' : '';
      return childPrefix + toCompactJSON(item, indent + 2) + comma;
    }).join('\n');
    return '[\n' + items + '\n' + prefix + ']';
  }

  if (typeof obj === 'object') {
    const keys = Object.keys(obj);
    if (keys.length === 0) return '{}';
    const items = keys.map((key, i) => {
      const comma = i < keys.length - 1 ? ',' : '';
      const jsonKey = JSON.stringify(key);
      return childPrefix + jsonKey + ': ' + toCompactJSON(obj[key], indent + 2) + comma;
    }).join('\n');
    return '{\n' + items + '\n' + prefix + '}';
  }

  return JSON.stringify(obj);
}

function getTimestamp() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// --- Activity Log Entry ---
function formatLogEntry(type, detail) {
  return { time: getTimestamp(), type, detail };
}

// --- Interval Bar Component ---
function IntervalBar({ interval, color, label, minVal, maxVal, height }) {
  const range = maxVal - minVal || 1;
  const leftPct = ((interval[0] - minVal) / range) * 100;
  const widthPct = ((interval[1] - interval[0]) / range) * 100;
  const h = height || 32;

  return (
    <div className="interval-bar-wrapper" style={{ height: h + 8 }}>
      <div
        className={'interval-bar ' + (color || 'blue')}
        style={{
          left: leftPct + '%',
          width: Math.max(widthPct, 2) + '%',
          height: h,
          minWidth: '40px'
        }}
        title={formatInterval(interval)}
      >
        <span className="interval-bar-label">{label || formatInterval(interval)}</span>
      </div>
    </div>
  );
}

// --- Main App ---
export default function App() {
  // Visualization state
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const autoPlayRef = useRef(null);

  // Checkpoint state
  const [checkpointSelections, setCheckpointSelections] = useState({});
  const [checkpointTextInputs, setCheckpointTextInputs] = useState({});
  const [checkpointSubmitted, setCheckpointSubmitted] = useState({});
  const [checkpointFeedback, setCheckpointFeedback] = useState({});
  const [hintsRevealed, setHintsRevealed] = useState({});
  const [answersRevealed, setAnswersRevealed] = useState({});

  // Activity log
  const [activityLog, setActivityLog] = useState([]);

  // Tab state
  const [activeTab, setActiveTab] = useState('visualize');

  const addLog = useCallback((type, detail) => {
    setActivityLog((prev) => [formatLogEntry(type, detail), ...prev].slice(0, 50));
  }, []);

  // Auto-play
  useEffect(() => {
    if (autoPlay) {
      autoPlayRef.current = setInterval(() => {
        setCurrentStepIdx((prev) => {
          if (prev >= steps.length - 1) {
            setAutoPlay(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
    } else {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    }
    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, [autoPlay]);

  const goToStep = (idx) => {
    const clamped = Math.max(0, Math.min(idx, steps.length - 1));
    setCurrentStepIdx(clamped);
    addLog('navigation', 'Navigated to step ' + clamped + ' (' + steps[clamped].title + ')');
  };

  const goNext = () => goToStep(currentStepIdx + 1);
  const goPrev = () => goToStep(currentStepIdx - 1);
  const resetSteps = () => {
    setCurrentStepIdx(0);
    setAutoPlay(false);
    addLog('navigation', 'Reset visualization to step 0');
  };

  const currentStep = steps[currentStepIdx];
  const isLastStep = currentStepIdx === steps.length - 1;
  const isFirstStep = currentStepIdx === 0;

  // Compute range for interval bars
  const allValues = problemInput.intervals.flat();
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);

  // Compact JSON strings for display
  const inputJSON = toCompactJSON(problemInput);
  const answerJSON = toCompactJSON(expectedAnswer);

  // --- Checkpoint handlers ---
  const handleCheckpointSelect = (qId, value) => {
    setCheckpointSelections((prev) => ({ ...prev, [qId]: value }));
  };

  const handleCheckpointTextInput = (qId, value) => {
    setCheckpointTextInputs((prev) => ({ ...prev, [qId]: value }));
  };

  const submitCheckpoint = (qId) => {
    const cp = checkpoints.find((c) => c.id === qId);
    if (!cp) return;

    let isCorrect = false;
    let userAnswer = '';

    if (cp.type === 'multiple-choice') {
      userAnswer = checkpointSelections[qId] || '(no selection)';
      isCorrect = checkpointSelections[qId] === cp.correctAnswer;
    } else if (cp.type === 'text-input') {
      userAnswer = checkpointTextInputs[qId] || '(empty)';
      const normalized = (userAnswer || '').replace(/\s+/g, '');
      const expected = cp.correctAnswer.replace(/\s+/g, '');
      isCorrect = normalized === expected;
    }

    setCheckpointSubmitted((prev) => ({ ...prev, [qId]: true }));
    setCheckpointFeedback((prev) => ({
      ...prev,
      [qId]: isCorrect ? 'correct' : 'incorrect'
    }));

    if (isCorrect) {
      addLog('checkpoint-correct', 'Q' + qId.slice(1) + ': Answered correctly — "' + userAnswer + '"');
    } else {
      addLog('checkpoint-incorrect', 'Q' + qId.slice(1) + ': Answered incorrectly — "' + userAnswer + '"');
    }
  };

  const revealHint = (qId) => {
    setHintsRevealed((prev) => ({ ...prev, [qId]: true }));
    addLog('hint', 'Revealed hint for question ' + qId.slice(1));
  };

  const revealAnswer = (qId) => {
    setAnswersRevealed((prev) => ({ ...prev, [qId]: true }));
    addLog('show-answer', 'Revealed answer for question ' + qId.slice(1));
  };

  const resetCheckpoint = (qId) => {
    setCheckpointSelections((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    setCheckpointTextInputs((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    setCheckpointSubmitted((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    setCheckpointFeedback((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    setHintsRevealed((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    setAnswersRevealed((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
    addLog('reset', 'Reset checkpoint question ' + qId.slice(1));
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">Merge Intervals</h1>
        <span className="app-badge algorithm-badge">Greedy Algorithm</span>
      </header>

      {/* Main layout */}
      <div className="main-layout">
        {/* Left column: Problem + Visualization */}
        <div className="left-column">
          {/* Problem Description */}
          <section className="card problem-card">
            <h2 className="card-title">Problem Statement</h2>
            <p className="problem-text">
              The conference center receives multiple venue occupancy requests. Each closed interval{' '}
              <code>[start time, end time]</code> in <code>intervals</code> represents a reservation slot.
              Since the same room cannot be used simultaneously, all overlapping or contiguous slots need
              to be merged, returning the final list of non-overlapping occupied intervals sorted by start time.
            </p>

            <div className="io-section">
              <div className="io-block">
                <h3 className="io-label">Input</h3>
                <pre className="io-data input-data">{inputJSON}</pre>
              </div>
              <div className="io-block">
                <h3 className="io-label">Expected Answer</h3>
                <pre className="io-data answer-data">{answerJSON}</pre>
              </div>
            </div>

            <h3 className="subsection-title">Learning Objectives</h3>
            <ul className="objectives-list">
              {learningObjectives.map((obj, i) => (
                <li key={i} className="objective-item">{obj}</li>
              ))}
            </ul>
          </section>

          {/* Tab Navigation */}
          <div className="tab-bar">
            <button
              className={'tab-btn' + (activeTab === 'visualize' ? ' active' : '')}
              onClick={() => setActiveTab('visualize')}
            >
              Step Visualization
            </button>
            <button
              className={'tab-btn' + (activeTab === 'checkpoints' ? ' active' : '')}
              onClick={() => setActiveTab('checkpoints')}
            >
              Checkpoint Questions
            </button>
          </div>

          {/* Visualization Panel */}
          {activeTab === 'visualize' && (
            <section className="card viz-card">
              <h2 className="card-title">Algorithm Step-by-Step</h2>

              {/* Step info */}
              <div className="step-info-bar">
                <span className="step-badge">
                  Step {currentStepIdx} / {steps.length - 1}
                </span>
                <span className="step-title-text">{currentStep.title}</span>
                <span
                  className={
                    'action-tag ' +
                    (currentStep.action === 'extend'
                      ? 'action-extend'
                      : currentStep.action === 'append'
                      ? 'action-append'
                      : 'action-init')
                  }
                >
                  {currentStep.action === 'extend'
                    ? 'EXTEND'
                    : currentStep.action === 'append'
                    ? 'APPEND'
                    : 'INIT'}
                </span>
              </div>

              <p className="step-description">{currentStep.description}</p>

              {currentStep.comparisonDetail && (
                <div className="comparison-box">
                  <span className="comparison-icon">🔍</span>
                  <span>{currentStep.comparisonDetail}</span>
                </div>
              )}

              {/* Sorted intervals timeline */}
              <div className="viz-section">
                <h4 className="viz-section-title">Sorted Intervals (input)</h4>
                <div className="timeline-container">
                  <div className="timeline-axis">
                    {Array.from({ length: maxVal - minVal + 1 }, (_, i) => minVal + i).map((v) => (
                      <span key={v} className="axis-tick" style={{ left: ((v - minVal) / (maxVal - minVal || 1)) * 100 + '%' }}>
                        {v}
                      </span>
                    ))}
                  </div>
                  {currentStep.sortedIntervals.map((iv, i) => {
                    let color = 'bar-pending';
                    if (i < currentStep.currentIndex) color = 'bar-processed';
                    else if (i === currentStep.currentIndex) color = 'bar-current';
                    return (
                      <IntervalBar
                        key={i}
                        interval={iv}
                        color={color}
                        label={formatInterval(iv)}
                        minVal={minVal}
                        maxVal={maxVal}
                        height={30}
                      />
                    );
                  })}
                </div>
                <div className="bar-legend">
                  <span className="legend-item"><span className="legend-dot bar-current-dot"></span>Current</span>
                  <span className="legend-item"><span className="legend-dot bar-processed-dot"></span>Processed</span>
                  <span className="legend-item"><span className="legend-dot bar-pending-dot"></span>Pending</span>
                </div>
              </div>

              {/* Merged result */}
              <div className="viz-section">
                <h4 className="viz-section-title">Merged Result</h4>
                <div className="timeline-container merged-timeline">
                  <div className="timeline-axis">
                    {Array.from({ length: maxVal - minVal + 1 }, (_, i) => minVal + i).map((v) => (
                      <span key={v} className="axis-tick" style={{ left: ((v - minVal) / (maxVal - minVal || 1)) * 100 + '%' }}>
                        {v}
                      </span>
                    ))}
                  </div>
                  {currentStep.merged.map((iv, i) => (
                    <IntervalBar
                      key={i}
                      interval={iv}
                      color="bar-merged"
                      label={formatInterval(iv)}
                      minVal={minVal}
                      maxVal={maxVal}
                      height={36}
                    />
                  ))}
                </div>
                <pre className="merged-code">{formatMerged(currentStep.merged)}</pre>
              </div>

              {/* Controls */}
              <div className="viz-controls">
                <button className="ctrl-btn" onClick={resetSteps} disabled={isFirstStep && !autoPlay} title="Reset to beginning">
                  ⏮ Reset
                </button>
                <button className="ctrl-btn" onClick={goPrev} disabled={isFirstStep} title="Previous step">
                  ◀ Prev
                </button>
                <span className="step-counter">
                  {currentStepIdx} / {steps.length - 1}
                </span>
                <button className="ctrl-btn" onClick={goNext} disabled={isLastStep} title="Next step">
                  Next ▶
                </button>
                <button
                  className={'ctrl-btn ctrl-auto' + (autoPlay ? ' active' : '')}
                  onClick={() => { setAutoPlay(!autoPlay); addLog('navigation', autoPlay ? 'Stopped auto-play' : 'Started auto-play'); }}
                  title="Auto-play steps"
                >
                  {autoPlay ? '⏸ Pause' : '▶ Auto Play'}
                </button>
              </div>

              {/* Progress bar */}
              <div className="progress-bar-container">
                <div
                  className="progress-bar-fill"
                  style={{ width: ((currentStepIdx / (steps.length - 1)) * 100) + '%' }}
                ></div>
              </div>
            </section>
          )}

          {/* Checkpoint Panel */}
          {activeTab === 'checkpoints' && (
            <section className="card checkpoint-card">
              <h2 className="card-title">Checkpoint Questions</h2>
              <p className="checkpoint-intro">
                Test your understanding of the Merge Intervals algorithm. Answer each question and get immediate feedback.
              </p>

              {checkpoints.map((cp) => {
                const submitted = checkpointSubmitted[cp.id];
                const feedback = checkpointFeedback[cp.id];
                const hintShown = hintsRevealed[cp.id];
                const answerShown = answersRevealed[cp.id];

                return (
                  <div key={cp.id} className={'checkpoint-item' + (submitted ? (feedback === 'correct' ? ' cp-correct' : ' cp-incorrect') : '')}>
                    <h3 className="checkpoint-question">
                      <span className="cp-num">Q{cp.id.slice(1)}</span> {cp.question}
                    </h3>

                    {cp.type === 'multiple-choice' && (
                      <div className="cp-options">
                        {cp.options.map((opt) => {
                          const isSelected = checkpointSelections[cp.id] === opt.value;
                          const isCorrectOption = opt.value === cp.correctAnswer;
                          let optClass = 'cp-option';
                          if (submitted) {
                            if (isCorrectOption) optClass += ' opt-correct';
                            else if (isSelected && !isCorrectOption) optClass += ' opt-wrong';
                          } else if (isSelected) {
                            optClass += ' opt-selected';
                          }
                          return (
                            <label key={opt.value} className={optClass}>
                              <input
                                type="radio"
                                name={'cp-' + cp.id}
                                value={opt.value}
                                checked={isSelected || false}
                                onChange={() => handleCheckpointSelect(cp.id, opt.value)}
                                disabled={submitted && feedback === 'correct'}
                              />
                              <span className="opt-label">{opt.label}</span>
                              {submitted && isCorrectOption && <span className="opt-mark correct-mark">✓ Correct</span>}
                              {submitted && isSelected && !isCorrectOption && <span className="opt-mark wrong-mark">✗ Incorrect</span>}
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {cp.type === 'text-input' && (
                      <div className="cp-text-input-area">
                        <label className="cp-input-label">
                          Enter the modified interval (format: start,end):
                          <input
                            type="text"
                            className={'cp-text-input' + (submitted ? (feedback === 'correct' ? ' input-correct' : ' input-incorrect') : '')}
                            placeholder="e.g., 8,9"
                            value={checkpointTextInputs[cp.id] || ''}
                            onChange={(e) => handleCheckpointTextInput(cp.id, e.target.value)}
                            disabled={submitted && feedback === 'correct'}
                            onKeyDown={(e) => { if (e.key === 'Enter') submitCheckpoint(cp.id); }}
                          />
                        </label>
                        {submitted && feedback === 'correct' && <span className="feedback-msg feedback-correct">✓ Correct!</span>}
                        {submitted && feedback === 'incorrect' && <span className="feedback-msg feedback-incorrect">✗ Not quite. Try again or use the hint.</span>}
                      </div>
                    )}

                    {submitted && cp.type === 'multiple-choice' && (
                      <div className={'feedback-msg' + (feedback === 'correct' ? ' feedback-correct' : ' feedback-incorrect')}>
                        {feedback === 'correct'
                          ? '✓ Correct! ' + cp.explanation
                          : '✗ Incorrect. ' + (answerShown ? cp.explanation : 'Try using a hint or revealing the answer.')}
                      </div>
                    )}

                    <div className="cp-actions">
                      {(!submitted || feedback !== 'correct') && (
                        <button
                          className="cp-action-btn btn-submit"
                          onClick={() => submitCheckpoint(cp.id)}
                          disabled={submitted && feedback === 'correct'}
                        >
                          Submit Answer
                        </button>
                      )}
                      <button
                        className="cp-action-btn btn-hint"
                        onClick={() => revealHint(cp.id)}
                      >
                        {hintShown ? 'Hint' : 'Show Hint'}
                      </button>
                      <button
                        className="cp-action-btn btn-reveal"
                        onClick={() => revealAnswer(cp.id)}
                      >
                        Show Answer
                      </button>
                      <button
                        className="cp-action-btn btn-reset-cp"
                        onClick={() => resetCheckpoint(cp.id)}
                      >
                        Retry
                      </button>
                    </div>

                    {hintShown && (
                      <div className="hint-box">
                        <span className="hint-icon">💡</span>
                        <span>{cp.hint}</span>
                      </div>
                    )}

                    {answerShown && (
                      <div className="answer-reveal-box">
                        <span className="answer-icon">📖</span>
                        <div>
                          <strong>Answer:</strong>{' '}
                          {cp.type === 'multiple-choice'
                            ? cp.options.find((o) => o.value === cp.correctAnswer).label
                            : cp.correctAnswer}
                          <br />
                          <span className="answer-explanation">{cp.explanation}</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </section>
          )}
        </div>

        {/* Right column: Activity Log */}
        <aside className="right-column">
          <div className="card log-card">
            <h2 className="card-title">
              <span className="log-title-icon">📝</span> Learning Activity Log
            </h2>
            {activityLog.length === 0 ? (
              <p className="log-empty">No activity yet. Interact with the visualization or checkpoint questions to see your actions logged here.</p>
            ) : (
              <ul className="log-list">
                {activityLog.map((entry, i) => (
                  <li key={i} className={'log-entry log-' + entry.type}>
                    <span className="log-time">{entry.time}</span>
                    <span className="log-detail">{entry.detail}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <p>Merge Intervals — Interactive Algorithm Learning Tool © 2024</p>
      </footer>
    </div>
  );
}
