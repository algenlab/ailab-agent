import React, { useState, useCallback, useMemo } from 'react';

// --- Graph data and algorithm ---
const GRAPH = {
  A: ['B', 'C'],
  B: ['D'],
  C: ['D'],
  D: []
};

const EXPECTED_ANSWER = ['A', 'B', 'C', 'D'];

// Node positions for the SVG graph diagram
const NODE_POSITIONS = {
  A: { x: 200, y: 40 },
  B: { x: 100, y: 160 },
  C: { x: 300, y: 160 },
  D: { x: 200, y: 270 }
};

const EDGES = [
  { from: 'A', to: 'B' },
  { from: 'A', to: 'C' },
  { from: 'B', to: 'D' },
  { from: 'C', to: 'D' }
];

// Visual graph diagram component
function GraphDiagram() {
  return (
    <div className="graph-svg-container">
      <svg width="400" height="320" viewBox="0 0 400 320" aria-label="Graph diagram showing course dependencies">
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="10"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
          </marker>
        </defs>

        {/* Edges */}
        {EDGES.map((edge) => {
          const from = NODE_POSITIONS[edge.from];
          const to = NODE_POSITIONS[edge.to];
          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const len = Math.sqrt(dx * dx + dy * dy);
          const ux = dx / len;
          const uy = dy / len;
          const startX = from.x + ux * 24;
          const startY = from.y + uy * 24;
          const endX = to.x - ux * 26;
          const endY = to.y - uy * 26;
          return (
            <line
              key={`edge-${edge.from}-${edge.to}`}
              x1={startX}
              y1={startY}
              x2={endX}
              y2={endY}
              stroke="#64748b"
              strokeWidth="2"
              markerEnd="url(#arrowhead)"
            />
          );
        })}

        {/* Nodes */}
        {Object.entries(NODE_POSITIONS).map(([label, pos]) => (
          <g key={label}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r="22"
              fill="#dbeafe"
              stroke="#2563eb"
              strokeWidth="2"
            />
            <text
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fill="#1e40af"
              fontWeight="700"
              fontSize="16"
              fontFamily="'Segoe UI', system-ui, sans-serif"
            >
              {label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function generateSteps() {
  const indegree = {};
  const queue = [];
  const sorted = [];
  const steps = [];

  for (const node in GRAPH) {
    indegree[node] = 0;
  }
  for (const node in GRAPH) {
    for (const neighbor of GRAPH[node]) {
      indegree[neighbor] = (indegree[neighbor] || 0) + 1;
    }
  }

  for (const node in indegree) {
    if (indegree[node] === 0) {
      queue.push(node);
    }
  }

  // Step 0: initial state before any pop
  steps.push({
    indegree: { ...indegree },
    queue: [...queue],
    sorted: [...sorted],
    popped: null,
    description: 'Initial state: compute indegrees and enqueue all nodes with indegree 0.'
  });

  while (queue.length > 0) {
    const node = queue.shift();
    sorted.push(node);

    for (const neighbor of GRAPH[node]) {
      indegree[neighbor]--;
      if (indegree[neighbor] === 0) {
        queue.push(neighbor);
      }
    }

    steps.push({
      indegree: { ...indegree },
      queue: [...queue],
      sorted: [...sorted],
      popped: node,
      description: `Pop "${node}" from queue, process its neighbors, update indegrees.`
    });
  }

  return steps;
}

const STEPS = generateSteps();

// --- Main App Component ---
export default function App() {
  const [stepIndex, setStepIndex] = useState(0);
  const [checkpointAnswer, setCheckpointAnswer] = useState(null);
  const [checkpointSubmitted, setCheckpointSubmitted] = useState(false);
  const [checkpointCorrect, setCheckpointCorrect] = useState(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const [logEntries, setLogEntries] = useState([]);

  const currentStep = STEPS[stepIndex] || STEPS[STEPS.length - 1];

  // Determine if we're at the checkpoint step (after popping A, before popping B)
  const atCheckpointStep = useMemo(() => {
    if (stepIndex >= STEPS.length) return false;
    const s = STEPS[stepIndex];
    return s.sorted.length === 1 && s.sorted[0] === 'A' && s.queue.length > 0 && s.queue[0] === 'B';
  }, [stepIndex]);

  const addLog = useCallback((message) => {
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogEntries(prev => [...prev, { time, message }]);
  }, []);

  const handleStepChange = useCallback((delta) => {
    setStepIndex(prev => {
      const next = Math.max(0, Math.min(STEPS.length - 1, prev + delta));
      if (next !== prev) {
        addLog(`Navigated to step ${next} (${STEPS[next].description})`);
      }
      return next;
    });
  }, [addLog]);

  const handleCheckpointSubmit = useCallback(() => {
    if (checkpointAnswer === null) return;
    const correctAnswer = 'None';
    const isCorrect = checkpointAnswer === correctAnswer;
    setCheckpointSubmitted(true);
    setCheckpointCorrect(isCorrect);
    addLog(`Checkpoint answer submitted: "${checkpointAnswer}" - ${isCorrect ? 'Correct' : 'Incorrect'}`);
  }, [checkpointAnswer, addLog]);

  const handleHint = useCallback(() => {
    setHintVisible(true);
    addLog('Hint requested');
  }, [addLog]);

  const handleShowAnswer = useCallback(() => {
    setAnswerRevealed(true);
    addLog('Answer revealed');
  }, [addLog]);

  const resetCheckpoint = useCallback(() => {
    setCheckpointAnswer(null);
    setCheckpointSubmitted(false);
    setCheckpointCorrect(null);
    setHintVisible(false);
    setAnswerRevealed(false);
  }, []);

  const handleOptionSelect = useCallback((value) => {
    if (!checkpointSubmitted) {
      setCheckpointAnswer(value);
    }
  }, [checkpointSubmitted]);

  const isStepFirst = stepIndex === 0;
  const isStepLast = stepIndex === STEPS.length - 1;

  return (
    <div className="container">
      <header style={{ marginBottom: '1rem', textAlign: 'center', paddingTop: '1rem' }}>
        <h1>Topological Sort</h1>
        <p style={{ color: 'var(--text-secondary)' }}>BFS/DFS Basic Graph · Interactive Learning</p>
      </header>

      <div className="page-grid">
        {/* Input & Graph Diagram */}
        <div className="card">
          <div className="section-title">Course Dependency Graph (Input)</div>
          {Object.entries(GRAPH).map(([node, neighbors]) => (
            <div className="graph-row" key={node}>
              <span className="graph-node">{node}</span>
              <span className="graph-edge">→</span>
              {neighbors.length > 0 ? neighbors.map((n, i) => (
                <span key={n}>
                  <span className="graph-node">{n}</span>
                  {i < neighbors.length - 1 && <span className="graph-edge">,</span>}
                </span>
              )) : <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>(none)</span>}
            </div>
          ))}
          <GraphDiagram />
        </div>

        {/* Expected Answer & Learning Objectives */}
        <div className="card">
          <div className="section-title">Expected Final Answer</div>
          <div className="sorted-list">
            {EXPECTED_ANSWER.map((node, i) => (
              <span key={i}>
                <span className="sorted-item">{node}</span>
                {i < EXPECTED_ANSWER.length - 1 && <span style={{ color: 'var(--text-secondary)', margin: '0 0.25rem' }}>→</span>}
              </span>
            ))}
          </div>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            A valid topological ordering: [A, B, C, D]
          </p>

          <div style={{ marginTop: '1.25rem' }}>
            <div className="section-title">Learning Objectives</div>
            <ul className="objectives-list">
              <li>Understand how the indegree table records the remaining dependency count.</li>
              <li>Master the strategy of using a queue to manage zero indegree nodes.</li>
              <li>Be able to predict the state updates after popping a node at each step from a trace.</li>
            </ul>
          </div>
        </div>

        {/* Algorithm Visualization */}
        <div className="card full-width">
          <div className="section-title">Step-by-Step Visualization</div>

          {/* Step navigation */}
          <div className="btn-group" style={{ marginBottom: '1rem' }}>
            <button onClick={() => handleStepChange(-1)} disabled={isStepFirst}>
              ← Previous
            </button>
            <button onClick={() => handleStepChange(1)} disabled={isStepLast}>
              Next →
            </button>
            <span style={{ padding: '0.5rem', fontWeight: 600 }}>
              Step {stepIndex} / {STEPS.length - 1}
            </span>
          </div>

          <p style={{ marginBottom: '0.75rem', fontStyle: 'italic', color: 'var(--text-secondary)' }}>
            {currentStep.description}
          </p>

          {/* State tables */}
          <div className="vis-grid">
            <div>
              <h3>Indegree Table</h3>
              <table className="vis-table">
                <thead>
                  <tr>
                    <th>Node</th>
                    <th>Indegree</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(currentStep.indegree).map(([node, degree]) => (
                    <tr key={node} className={degree === 0 ? 'highlight' : ''}>
                      <td><span className="graph-node">{node}</span></td>
                      <td>{degree}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h3>Processing Queue</h3>
              <div className="queue-display">
                {currentStep.queue.length === 0 ? (
                  <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>Empty</span>
                ) : (
                  currentStep.queue.map((node, i) => (
                    <span key={i} className={`queue-item ${i === 0 ? 'head' : ''}`}>
                      {node}
                    </span>
                  ))
                )}
              </div>
              {currentStep.popped && (
                <div style={{ marginTop: '0.75rem' }}>
                  <strong>Last popped:</strong> <span className="graph-node">{currentStep.popped}</span>
                </div>
              )}
              <div style={{ marginTop: '0.75rem' }}>
                <h3>Sorted Order</h3>
                <div className="sorted-list">
                  {currentStep.sorted.length === 0 ? (
                    <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>None yet</span>
                  ) : (
                    currentStep.sorted.map((node, i) => (
                      <span key={i} className="sorted-item">{node}</span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Checkpoint */}
          {atCheckpointStep && (
            <div className="checkpoint-prompt">
              <h3 style={{ color: 'var(--warning)' }}>Knowledge Checkpoint</h3>
              <p style={{ marginBottom: '0.5rem' }}>
                <strong>Question:</strong> The current head of the queue is <span className="graph-node">B</span>.
                Please predict <strong>which neighbors' indegree will become 0</strong> and will be added to the queue after popping <span className="graph-node">B</span>.
              </p>
              <div className="options-grid">
                {['A', 'C', 'D', 'None'].map(opt => (
                  <button
                    key={opt}
                    className={`option-btn ${checkpointAnswer === opt ? 'selected' : ''}`}
                    onClick={() => handleOptionSelect(opt)}
                    disabled={checkpointSubmitted}
                  >
                    {opt}
                  </button>
                ))}
              </div>

              <div className="btn-group" style={{ marginTop: '0.5rem' }}>
                <button
                  className="primary"
                  onClick={handleCheckpointSubmit}
                  disabled={checkpointAnswer === null || checkpointSubmitted}
                >
                  Submit Answer
                </button>
                <button onClick={handleHint} disabled={hintVisible}>
                  Hint
                </button>
                <button onClick={handleShowAnswer} disabled={answerRevealed}>
                  Show Answer
                </button>
                {checkpointSubmitted && (
                  <button onClick={resetCheckpoint}>Try Again</button>
                )}
              </div>

              {hintVisible && (
                <div className="hint-box">
                  <strong>Hint:</strong> Look at the neighbors of node B in the original graph. Decrement their indegree by 1 and check if any reaches 0.
                </div>
              )}

              {answerRevealed && (
                <div className="answer-reveal">
                  <strong>Answer:</strong> None — B's only neighbor is D. After popping B, D's indegree drops from 2 to 1, which is still not 0. Therefore no new node enters the queue. The correct choice is <strong>None</strong>.
                </div>
              )}

              {checkpointSubmitted && (
                <div className={`feedback ${checkpointCorrect ? 'correct' : 'incorrect'}`}>
                  {checkpointCorrect
                    ? 'Correct! B has only neighbor D, whose indegree drops from 2 to 1 (still not 0), so no new node enters the queue.'
                    : <>Not quite. B has only neighbor D. D's indegree goes from 2 to 1, so it does <strong>not</strong> become 0. The correct answer is <strong>None</strong>.</>}
                </div>
              )}
            </div>
          )}

          {/* Cycle question note */}
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--primary-light)', borderRadius: '6px', fontSize: '0.9rem' }}>
            <strong>Reflection:</strong> If we added an edge <span className="graph-node">D</span> → <span className="graph-node">A</span>, the graph would contain a cycle.
            The algorithm would terminate with fewer nodes in <em>sorted</em> than total nodes, signaling that no valid topological order exists.
          </div>
        </div>

        {/* Activity Log */}
        <div className="card">
          <div className="section-title">Activity Log</div>
          <div className="log-container">
            {logEntries.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No actions yet. Start navigating or answering!</p>
            ) : (
              logEntries.map((entry, i) => (
                <div className="log-entry" key={i}>
                  <span className="log-time">{entry.time}</span>
                  <span>{entry.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
