import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { computeSteps } from './dijkstra';
import GraphViz from './GraphViz';
import JsonHighlight from './JsonHighlight';

// Problem data
const PROBLEM = {
  start: 'A',
  weighted_graph: {
    A: [
      ['B', 2],
      ['C', 5]
    ],
    B: [['C', 1]],
    C: []
  }
};

const FINAL_ANSWER = { A: 0, B: 2, C: 3 };

// Checkpoint definitions
const CHECKPOINTS = [
  {
    id: 'cp1',
    triggerStep: 1,
    question:
      'The current heap is [(2, B), (5, C)], distance records: A:0, B:2, C:5. Which node will be popped from the heap next?',
    type: 'single-choice',
    options: ['A', 'B', 'C'],
    correctIndex: 1,
    hint: 'A min-heap always pops the element with the smallest distance. Compare 2 and 5.',
    answerExplanation: 'B has the smallest distance (2) in the heap, so it will be popped next.'
  },
  {
    id: 'cp2',
    triggerStep: 2,
    question:
      'During execution, which of the following statements is an invariant that always holds?',
    type: 'single-choice',
    options: [
      'A) The heap size equals the number of unprocessed nodes',
      'B) The shortest distance of a popped node is never updated again',
      'C) The current distance of every node is the final shortest path'
    ],
    correctIndex: 1,
    hint: 'Think about what happens once a node is popped from the heap with its true shortest distance.',
    answerExplanation:
      "Once a node is popped from the heap with its minimum distance, that distance is final and will never be updated again. This is a fundamental invariant of Dijkstra's algorithm with non-negative edge weights."
  },
  {
    id: 'cp3',
    triggerStep: 999, // Show after algorithm completion
    question:
      'If start is changed to "B" and the weight of edge (A, C) is changed from 5 to 2, predict the shortest time from B to C.',
    type: 'number-input',
    correctAnswer: 1,
    hint: 'Start at B (distance 0). B has an edge to C with weight 1. The changed edge (A, C) does not help because A is not reachable from B in the opposite direction.',
    answerExplanation:
      'From B, the only outgoing edge is B\u2192C with weight 1, so the shortest time from B to C is 1.'
  },
  {
    id: 'cp4',
    triggerStep: 2,
    question:
      'Step 3: Pop node B (distance 2), find B\u2192C weight 1, candidate distance 3, while current C distance is 5, so update C distance to 3. Explain why this distance update was triggered.',
    type: 'single-choice',
    options: [
      'The heap was empty',
      'A shorter path A\u2192B\u2192C (2+1=3) was found compared to the direct A\u2192C (5)',
      'Node C was already visited'
    ],
    correctIndex: 1,
    hint: 'The new candidate distance 2 + 1 = 3 is less than the previously known distance to C.',
    answerExplanation:
      'The path A\u2192B\u2192C gives a total travel time of 3, which is shorter than the direct edge A\u2192C with time 5. Relaxation updates the distance to the smaller value.'
  }
];

export default function App() {
  // Algorithm steps are always computed (not dependent on start)
  const { steps, finalDist } = useMemo(
    () => computeSteps(PROBLEM.start, PROBLEM.weighted_graph),
    []
  );

  const [hasStarted, setHasStarted] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [log, setLog] = useState([]);
  const [checkpointState, setCheckpointState] = useState({});
  const scrollRef = useRef(null);

  const currentStep = steps[stepIndex] || steps[0];
  const maxStep = steps.length - 1;

  // Determine which checkpoints are active at current step (only after start)
  const activeCheckpoints = hasStarted
    ? CHECKPOINTS.filter((cp) => {
        if (cp.triggerStep === 999) return stepIndex === maxStep;
        return cp.triggerStep === stepIndex;
      })
    : [];

  const addLog = useCallback((msg) => {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour12: false });
    setLog((prev) => [...prev, { time, msg }]);
  }, []);

  // Auto-scroll log
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [log]);

  const handleRun = useCallback(() => {
    setHasStarted(true);
    setStepIndex(0);
    setCheckpointState({});
    setLog([]);
    addLog('Algorithm simulation started. Initial state ready.');
  }, [addLog]);

  const goToStep = useCallback(
    (idx) => {
      if (idx >= 0 && idx <= maxStep) {
        setStepIndex(idx);
        addLog('Navigated to step ' + idx + ' of ' + maxStep);
      }
    },
    [maxStep, addLog]
  );

  const resetCheckpoints = useCallback(() => {
    setCheckpointState({});
    addLog('Reset all checkpoints');
  }, [addLog]);

  // Checkpoint interaction handlers
  const handleOptionSelect = (cpId, optionIndex) => {
    setCheckpointState((prev) => ({
      ...prev,
      [cpId]: { ...prev[cpId], selectedOption: optionIndex, submitted: false }
    }));
  };

  const submitCheckpoint = (cp) => {
    const state = checkpointState[cp.id] || {};
    const selected = state.selectedOption;
    if (selected === undefined) return;

    const isCorrect = selected === cp.correctIndex;
    setCheckpointState((prev) => ({
      ...prev,
      [cp.id]: { ...prev[cp.id], submitted: true, isCorrect }
    }));
    addLog(
      'Checkpoint "' +
        cp.question.slice(0, 50) +
        '..." answered ' +
        (isCorrect ? 'correctly' : 'incorrectly') +
        ' (selected: ' +
        cp.options[selected] +
        ')'
    );
  };

  const handleNumberSubmit = (cp, value) => {
    const num = parseInt(value, 10);
    if (isNaN(num)) return;

    const isCorrect = num === cp.correctAnswer;
    setCheckpointState((prev) => ({
      ...prev,
      [cp.id]: { ...prev[cp.id], submitted: true, isCorrect, numberValue: num }
    }));
    addLog(
      'Checkpoint "' +
        cp.question.slice(0, 50) +
        '..." answered ' +
        (isCorrect ? 'correctly' : 'incorrectly') +
        ' (entered: ' +
        num +
        ')'
    );
  };

  const useHint = (cpId) => {
    setCheckpointState((prev) => ({
      ...prev,
      [cpId]: { ...prev[cpId], hintUsed: true }
    }));
    addLog('Used hint for checkpoint ' + cpId);
  };

  const showAnswer = (cpId) => {
    setCheckpointState((prev) => ({
      ...prev,
      [cpId]: { ...prev[cpId], answerRevealed: true }
    }));
    addLog('Revealed answer for checkpoint ' + cpId);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Dijkstra Shortest Path</h1>
        <p className="subtitle">Shortest Path / MST – Interactive Algorithm Explorer</p>
      </header>

      <div className="main-content">
        {/* Left column: core content */}
        <div className="left-column">
          {/* Problem input & answer */}
          <div className="card">
            <h2>Problem Statement</h2>
            <p style={{ marginBottom: '0.65rem', color: '#2d3436', fontSize: '0.9rem', lineHeight: 1.5 }}>
              The city emergency dispatch center maintains a non-negative time-cost directed road
              network, where each node represents an intersection and each edge weight represents the
              travel time from one intersection to another. Given a rescue vehicle's starting
              intersection <strong>{PROBLEM.start}</strong>, return the shortest travel time to all
              reachable intersections.
            </p>

            <div className="problem-layout">
              <div className="problem-details">
                <div className="label">Start Node</div>
                <div className="data-block compact">
                  <JsonHighlight data={PROBLEM.start} />
                </div>

                <div className="label" style={{ marginTop: '0.55rem' }}>
                  Weighted Graph (adjacency list)
                </div>
                <div className="data-block graph-json">
                  <JsonHighlight data={PROBLEM.weighted_graph} />
                </div>

                <div className="label" style={{ marginTop: '0.55rem' }}>
                  Expected Final Answer
                </div>
                <div className="data-block compact">
                  <JsonHighlight data={FINAL_ANSWER} />
                </div>
              </div>

              <div className="graph-viz-container">
                <span className="graph-label">Road Network Diagram</span>
                <GraphViz
                  graph={PROBLEM.weighted_graph}
                  start={PROBLEM.start}
                  highlightNode={hasStarted ? currentStep.current : null}
                  highlightEdge={
                    hasStarted && currentStep.relaxed.length > 0
                      ? currentStep.relaxed[0]
                      : null
                  }
                />
                <span
                  style={{
                    fontSize: '0.7rem',
                    color: '#636e72',
                    marginTop: '0.3rem',
                    textAlign: 'center'
                  }}
                >
                  Arrows show directed edges with travel-time weights
                </span>
              </div>
            </div>

            {/* Run / Re-run button */}
            {!hasStarted && (
              <div className="run-section">
                <button className="run-btn" onClick={handleRun}>
                  ▶ Run Algorithm Simulation
                </button>
                <p style={{ marginTop: '0.4rem', fontSize: '0.8rem', color: '#636e72' }}>
                  Explore Dijkstra's algorithm step by step with interactive checkpoints
                </p>
              </div>
            )}
          </div>

          {/* Step visualization (only visible after starting) */}
          {hasStarted && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <h2 style={{ marginBottom: 0 }}>Algorithm Simulation</h2>
                <button
                  className="nav-btn secondary"
                  onClick={() => {
                    setHasStarted(false);
                    addLog('Returned to problem overview');
                  }}
                  style={{ fontSize: '0.76rem', padding: '0.28rem 0.6rem' }}
                >
                  ← Back to Problem
                </button>
              </div>

              <div className="step-info">
                <span className="step-badge">
                  Step {stepIndex} / {maxStep}
                </span>
                {currentStep.current && (
                  <span className="step-badge" style={{ background: '#e17055' }}>
                    Current node: {currentStep.current}
                  </span>
                )}
                {currentStep.done && (
                  <span className="step-badge" style={{ background: '#00b894' }}>
                    Complete
                  </span>
                )}
                {currentStep.skipped && (
                  <span className="step-badge" style={{ background: '#fdcb6e', color: '#2d3436' }}>
                    Stale entry skipped
                  </span>
                )}
              </div>

              <div className="step-description">{currentStep.description}</div>

              {/* State display */}
              <div className="state-grid">
                <div className="state-item">
                  <h4>Distances</h4>
                  {Object.entries(currentStep.dist).map(([node, d]) => (
                    <div className="dist-row" key={node}>
                      <span className="node">{node}</span>
                      <span className={'dist' + (d === Infinity ? ' inf' : '')}>
                        {d === Infinity ? '\u221E' : d}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="state-item">
                  <h4>Min-Heap</h4>
                  {currentStep.heap.length === 0 ? (
                    <span style={{ color: '#b2bec3', fontStyle: 'italic' }}>empty</span>
                  ) : (
                    <div className="heap-items">
                      {currentStep.heap.map((h, i) => (
                        <span
                          key={i}
                          className={
                            'heap-item' +
                            (i === 0 && !currentStep.skipped ? ' popped' : '')
                          }
                        >
                          ({h.d}, {h.node})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Visited nodes */}
              <div className="state-item" style={{ marginBottom: '0.75rem' }}>
                <h4>Visited (popped with final distance)</h4>
                <div className="visited-nodes">
                  {currentStep.visited.length === 0 ? (
                    <span style={{ color: '#b2bec3', fontStyle: 'italic' }}>none yet</span>
                  ) : (
                    currentStep.visited.map((n, i) => (
                      <span className="visited-node" key={i}>
                        {n}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Relaxations */}
              {currentStep.relaxed.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <h4
                    style={{
                      fontSize: '0.76rem',
                      textTransform: 'uppercase',
                      color: '#636e72',
                      marginBottom: '0.2rem'
                    }}
                  >
                    Edge Relaxations
                  </h4>
                  {currentStep.relaxed.map((r, i) => (
                    <div className="relaxation-entry" key={i}>
                      {r.from} → {r.to} (weight {r.weight})
                      <br />
                      distance[{r.to}]:{' '}
                      <span className="old">
                        {r.oldDist === Infinity ? '\u221E' : r.oldDist}
                      </span>
                      {' \u2192 '}
                      <span className="new">{r.newDist}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Navigation */}
              <div className="nav-controls">
                <button
                  className="nav-btn secondary"
                  onClick={() => goToStep(0)}
                  disabled={stepIndex === 0}
                  aria-label="Go to first step"
                >
                  ⏮ First
                </button>
                <button
                  className="nav-btn"
                  onClick={() => goToStep(stepIndex - 1)}
                  disabled={stepIndex === 0}
                  aria-label="Go to previous step"
                >
                  ◀ Previous
                </button>
                <span className="step-counter">
                  Step {stepIndex} of {maxStep}
                </span>
                <button
                  className="nav-btn"
                  onClick={() => goToStep(stepIndex + 1)}
                  disabled={stepIndex === maxStep}
                  aria-label="Go to next step"
                >
                  Next ▶
                </button>
                <button
                  className="nav-btn secondary"
                  onClick={() => goToStep(maxStep)}
                  disabled={stepIndex === maxStep}
                  aria-label="Go to last step"
                >
                  ⏭ Last
                </button>
                <button
                  className="nav-btn secondary"
                  onClick={() => {
                    goToStep(0);
                    resetCheckpoints();
                  }}
                  aria-label="Reset to first step and clear checkpoints"
                >
                  ↺ Reset All
                </button>
              </div>
            </div>
          )}

          {/* Checkpoints (only visible after starting) */}
          {hasStarted &&
            activeCheckpoints.map((cp) => {
              const state = checkpointState[cp.id] || {};
              return (
                <div
                  className={'checkpoint' + (activeCheckpoints.length > 0 ? ' active' : '')}
                  key={cp.id}
                >
                  <h3>⚖ Checkpoint</h3>
                  <p className="checkpoint-question">{cp.question}</p>

                  {cp.type === 'single-choice' && (
                    <>
                      <div className="options">
                        {cp.options.map((opt, idx) => {
                          let cls = 'option';
                          if (state.selectedOption === idx) cls += ' selected';
                          if (state.submitted) {
                            if (idx === cp.correctIndex) cls += ' correct';
                            else if (state.selectedOption === idx) cls += ' incorrect';
                          }
                          return (
                            <div
                              key={idx}
                              className={cls}
                              onClick={() => {
                                if (!state.submitted) handleOptionSelect(cp.id, idx);
                              }}
                              role="radio"
                              aria-checked={state.selectedOption === idx}
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  if (!state.submitted) handleOptionSelect(cp.id, idx);
                                }
                              }}
                            >
                              <input
                                type="radio"
                                name={cp.id}
                                checked={state.selectedOption === idx}
                                onChange={() => {}}
                                disabled={state.submitted}
                              />
                              <span>{opt}</span>
                            </div>
                          );
                        })}
                      </div>
                      {!state.submitted && (
                        <button
                          className="nav-btn"
                          onClick={() => submitCheckpoint(cp)}
                          disabled={state.selectedOption === undefined}
                        >
                          Submit Answer
                        </button>
                      )}
                    </>
                  )}

                  {cp.type === 'number-input' && (
                    <>
                      <div style={{ marginBottom: '0.35rem' }}>
                        <input
                          type="number"
                          className="number-input"
                          placeholder="Enter number"
                          value={state.numberValue ?? ''}
                          onChange={(e) => {
                            if (!state.submitted) {
                              setCheckpointState((prev) => ({
                                ...prev,
                                [cp.id]: { ...prev[cp.id], numberValue: e.target.value }
                              }));
                            }
                          }}
                          disabled={state.submitted}
                          aria-label="Enter your numerical answer"
                        />
                        {!state.submitted && (
                          <button
                            className="nav-btn"
                            onClick={() => handleNumberSubmit(cp, state.numberValue)}
                          >
                            Submit
                          </button>
                        )}
                      </div>
                    </>
                  )}

                  {/* Feedback */}
                  {state.submitted && (
                    <div
                      className={'feedback ' + (state.isCorrect ? 'success' : 'error')}
                      role="alert"
                    >
                      {state.isCorrect
                        ? '\u2713 Correct! Well done.'
                        : '\u2717 Incorrect. Review the algorithm state and try again.'}
                    </div>
                  )}

                  {/* Hint / Show Answer */}
                  <div className="action-btns">
                    {!state.answerRevealed && (
                      <button className="hint-btn" onClick={() => useHint(cp.id)}>
                        💡 Hint
                      </button>
                    )}
                    <button className="answer-btn" onClick={() => showAnswer(cp.id)}>
                      👁 Show Answer
                    </button>
                  </div>

                  {state.hintUsed && <div className="hint-text">{cp.hint}</div>}
                  {state.answerRevealed && (
                    <div className="answer-text">{cp.answerExplanation}</div>
                  )}
                </div>
              );
            })}
        </div>

        {/* Right column: learning log */}
        <div className="right-column">
          <div className="log-container">
            <h3>📋 Learning Log</h3>
            <div className="log-scroll" ref={scrollRef}>
              {!hasStarted && log.length === 0 && (
                <div className="log-welcome">
                  <p>
                    <strong>Welcome!</strong> This interactive tool will help you understand how
                    Dijkstra's algorithm finds the shortest paths in a directed graph with
                    non-negative edge weights.
                  </p>
                  <p>
                    <strong>How to use this page:</strong>
                  </p>
                  <ul>
                    <li>
                      Click <strong>"Run Algorithm Simulation"</strong> to begin
                    </li>
                    <li>Step through each phase of the algorithm using the navigation controls</li>
                    <li>Answer the checkpoint questions that appear at key moments</li>
                    <li>Use hints and show-answer if you get stuck</li>
                    <li>All your actions will be recorded here in the log</li>
                  </ul>
                  <p>
                    The road network diagram shows intersections (nodes) and one-way roads (directed
                    edges) with their travel times. Start your exploration by running the simulation!
                  </p>
                </div>
              )}
              {hasStarted && log.length === 0 && (
                <div className="log-entries">
                  <div className="log-entry welcome">
                    <span className="message">
                      Simulation started. Use the navigation buttons to walk through each step of
                      Dijkstra's algorithm.
                    </span>
                  </div>
                </div>
              )}
              <div className="log-entries">
                {log.map((entry, i) => (
                  <div className="log-entry" key={i}>
                    <span className="timestamp">{entry.time}</span>
                    <span className="message">{entry.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
