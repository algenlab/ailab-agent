import React, { useState, useCallback, useRef, useEffect } from 'react';
import './App.css';

// LinkedList node class for internal representation
class ListNode {
  constructor(value) {
    this.value = value;
    this.next = null;
  }
}

// Build linked list from array
function buildList(values) {
  if (!values.length) return null;
  const nodes = values.map(v => new ListNode(v));
  for (let i = 0; i < nodes.length - 1; i++) {
    nodes[i].next = nodes[i + 1];
  }
  return { head: nodes[0], nodes };
}

// Serialize list to array for answer display
function listToArray(head) {
  const result = [];
  let curr = head;
  while (curr) {
    result.push(curr.value);
    curr = curr.next;
  }
  return result;
}

// Capture the full state of the reversal algorithm at a given step
function captureTrace(values) {
  if (!values.length) return [];

  const { head, nodes } = buildList(values);
  const steps = [];

  let prev = null;
  let curr = head;
  let next = null;
  let stepIdx = 0;

  // Initial state
  steps.push({
    step: stepIdx,
    prev: null,
    curr: curr ? curr.value : null,
    next: null,
    listSnapshot: listToArray(head),
    description: 'Initial state: the linked list is in visit order. prev = null, curr points to the head.'
  });

  while (curr) {
    stepIdx++;
    next = curr.next;
    curr.next = prev;
    prev = curr;
    curr = next;

    steps.push({
      step: stepIdx,
      prev: prev ? prev.value : null,
      curr: curr ? curr.value : null,
      next: next ? next.value : null,
      listSnapshot: listToArray(prev ? findHead(prev) : null),
      description: `Step ${stepIdx}: Set curr.next = prev, then advance prev and curr.`
    });
  }

  // Final state
  steps.push({
    step: stepIdx + 1,
    prev: prev ? prev.value : null,
    curr: null,
    next: null,
    listSnapshot: listToArray(prev),
    description: 'Complete: The linked list is now fully reversed. prev is the new head.',
    isComplete: true
  });

  return steps;
}

function findHead(node) {
  let curr = node;
  const result = [];
  while (curr) {
    result.push(curr.value);
    curr = curr.next;
  }
  return node;
}

// Checkpoint questions
const CHECKPOINTS = [
  {
    id: 1,
    question: "In the current trace, curr points to the node with value 2, prev points to the node with value 1, next points to the node with value 3. Predict which value curr.next will point to in the next step.",
    options: ["1", "2", "3", "null"],
    correctIndex: 0,
    hint: "Look at the operation 'curr.next = prev' — what does prev currently point to?",
    explanation: "In the next step, curr.next is set to prev (which holds value 1). So curr.next will point to the node with value 1."
  },
  {
    id: 2,
    question: "During the iterative reversal of the linked list, which statement remains true at every step? Please identify an invariant from the trace.",
    options: [
      "prev is always the head of the original list",
      "The nodes already processed form a correctly reversed prefix",
      "curr always points to the last node in the original list",
      "next is always null"
    ],
    correctIndex: 1,
    hint: "Think about what part of the list has been successfully reversed at each step.",
    explanation: "At every step, the nodes that have been processed (from the original head up to the node before curr) form a correctly reversed prefix. This is a key invariant."
  },
  {
    id: 3,
    question: "Original values are [1, 2, 3], reversed is [3, 2, 1]. If you delete the middle node 2 from the original list, what is the reversal result?",
    options: ["[3, 1]", "[1, 3]", "[3, 2, 1]", "[1]"],
    correctIndex: 0,
    hint: "If the original list is [1, 3] after deleting 2, reversing it gives [3, 1].",
    explanation: "The original list becomes [1, 3] after deleting node 2. Reversing [1, 3] yields [3, 1]."
  },
  {
    id: 4,
    question: "At step 2, the trace shows the operation 'curr.next = prev'. Please explain the purpose of this step.",
    options: [
      "To move prev forward",
      "To reverse the direction of the current node's pointer",
      "To skip over the current node",
      "To set up the next iteration's curr"
    ],
    correctIndex: 1,
    hint: "What happens to a node's outgoing arrow when you reassign its .next property?",
    explanation: "The operation 'curr.next = prev' reverses the current node's pointer so it points backward to the previously processed node instead of forward. This is the core reversal action."
  }
];

// Highlight JSON with syntax colors
function highlightJSON(text) {
  const lines = text.split('\n');
  return lines.map((line, lineIdx) => {
    const tokens = [];
    let remaining = line;
    const tokenRegex = /("(?:[^"\\]|\\.)*")\s*(:)|("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(\btrue\b|\bfalse\b)|(\bnull\b)|([\[\]{}])|(,)|(\s+)/g;
    let match;
    let lastIndex = 0;

    while ((match = tokenRegex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        const ws = line.slice(lastIndex, match.index);
        if (ws) tokens.push(<span key={`${lineIdx}-ws-${lastIndex}`}>{ws}</span>);
      }

      if (match[1] && match[2]) {
        tokens.push(<span key={`${lineIdx}-k-${match.index}`} className="syn-key">{match[1]}</span>);
        tokens.push(<span key={`${lineIdx}-c-${match.index}`} className="syn-colon">{match[2]}</span>);
      } else if (match[1]) {
        tokens.push(<span key={`${lineIdx}-s-${match.index}`} className="syn-string">{match[1]}</span>);
      } else if (match[3]) {
        tokens.push(<span key={`${lineIdx}-s-${match.index}`} className="syn-string">{match[3]}</span>);
      } else if (match[4]) {
        tokens.push(<span key={`${lineIdx}-n-${match.index}`} className="syn-number">{match[4]}</span>);
      } else if (match[5]) {
        tokens.push(<span key={`${lineIdx}-b-${match.index}`} className="syn-bool">{match[5]}</span>);
      } else if (match[6]) {
        tokens.push(<span key={`${lineIdx}-nl-${match.index}`} className="syn-null">{match[6]}</span>);
      } else if (match[7]) {
        tokens.push(<span key={`${lineIdx}-br-${match.index}`} className="syn-brace">{match[7]}</span>);
      } else if (match[8]) {
        tokens.push(<span key={`${lineIdx}-cm-${match.index}`} className="syn-comma">{match[8]}</span>);
      } else if (match[9]) {
        tokens.push(<span key={`${lineIdx}-ws2-${match.index}`}>{match[9]}</span>);
      }

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < line.length) {
      tokens.push(<span key={`${lineIdx}-rem`}>{line.slice(lastIndex)}</span>);
    }

    return <span key={lineIdx}>{tokens}{lineIdx < lines.length - 1 ? '\n' : ''}</span>;
  });
}

function App() {
  const inputValues = [1, 2, 3];
  const expectedOutput = [3, 2, 1];
  const traceSteps = useRef(captureTrace(inputValues));
  const steps = traceSteps.current;

  const inputJSON = JSON.stringify({ values: inputValues }, null, 2);
  const outputJSON = JSON.stringify(expectedOutput, null, 2);

  const [currentStep, setCurrentStep] = useState(0);
  const [checkpointIndex, setCheckpointIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const [activityLog, setActivityLog] = useState([]);
  const [checkpointAnswered, setCheckpointAnswered] = useState(false);
  const [sandboxValues, setSandboxValues] = useState([...inputValues]);
  const [sandboxResult, setSandboxResult] = useState(null);

  const logRef = useRef(null);

  const addLogEntry = useCallback((message) => {
    const now = new Date();
    const timestamp = now.toLocaleTimeString('en-US', { hour12: false });
    setActivityLog(prev => [...prev, { timestamp, message, id: Date.now() }]);
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [activityLog]);

  const currentTrace = steps[currentStep] || steps[0];
  const currentCheckpoint = CHECKPOINTS[checkpointIndex];

  const handleStepChange = (delta) => {
    const newStep = currentStep + delta;
    if (newStep >= 0 && newStep < steps.length) {
      setCurrentStep(newStep);
      setHintVisible(false);
      setAnswerRevealed(false);
      addLogEntry(`Navigated to step ${newStep} of ${steps.length - 1}.`);
    }
  };

  const handleAnswerSelect = (idx) => {
    if (checkpointAnswered) return;
    setSelectedAnswer(idx);
  };

  const handleSubmitAnswer = () => {
    if (selectedAnswer === null || checkpointAnswered) return;

    const isCorrect = selectedAnswer === currentCheckpoint.correctIndex;
    setCheckpointAnswered(true);

    if (isCorrect) {
      setFeedback({
        type: 'correct',
        message: `Correct! ${currentCheckpoint.explanation}`
      });
      addLogEntry(`Checkpoint ${checkpointIndex + 1}: Answered correctly — "${currentCheckpoint.options[selectedAnswer]}".`);
    } else {
      setFeedback({
        type: 'incorrect',
        message: `Not quite. Your answer was "${currentCheckpoint.options[selectedAnswer]}". ${currentCheckpoint.explanation}`
      });
      addLogEntry(`Checkpoint ${checkpointIndex + 1}: Answered incorrectly — chose "${currentCheckpoint.options[selectedAnswer]}". Correct answer is "${currentCheckpoint.options[currentCheckpoint.correctIndex]}".`);
    }
  };

  const handleShowHint = () => {
    setHintVisible(true);
    addLogEntry(`Requested hint for checkpoint ${checkpointIndex + 1}.`);
  };

  const handleShowAnswer = () => {
    setAnswerRevealed(true);
    setSelectedAnswer(currentCheckpoint.correctIndex);
    setCheckpointAnswered(true);
    setFeedback({
      type: 'correct',
      message: `Answer revealed: ${currentCheckpoint.options[currentCheckpoint.correctIndex]}. ${currentCheckpoint.explanation}`
    });
    addLogEntry(`Revealed answer for checkpoint ${checkpointIndex + 1}: "${currentCheckpoint.options[currentCheckpoint.correctIndex]}".`);
  };

  const handleNextCheckpoint = () => {
    if (checkpointIndex < CHECKPOINTS.length - 1) {
      setCheckpointIndex(prev => prev + 1);
      setSelectedAnswer(null);
      setFeedback(null);
      setHintVisible(false);
      setAnswerRevealed(false);
      setCheckpointAnswered(false);
      addLogEntry(`Moved to checkpoint ${checkpointIndex + 2}.`);
    }
  };

  const handleSandboxChange = (index, newVal) => {
    const updated = [...sandboxValues];
    const parsed = parseInt(newVal, 10);
    updated[index] = isNaN(parsed) ? 0 : parsed;
    setSandboxValues(updated);
  };

  const handleSandboxAdd = () => {
    setSandboxValues(prev => [...prev, 0]);
    setSandboxResult(null);
    addLogEntry('Added a node to the sandbox list.');
  };

  const handleSandboxRemove = (index) => {
    if (sandboxValues.length <= 1) return;
    const updated = sandboxValues.filter((_, i) => i !== index);
    setSandboxValues(updated);
    setSandboxResult(null);
    addLogEntry(`Removed node at position ${index} from sandbox list.`);
  };

  const handleSandboxReverse = () => {
    const cleanValues = sandboxValues.filter(v => !isNaN(v));
    const reversed = [...cleanValues].reverse();
    setSandboxResult(reversed);
    addLogEntry(`Sandbox: Reversed [${cleanValues.join(', ')}] → [${reversed.join(', ')}].`);
  };

  const handleReset = () => {
    setCurrentStep(0);
    setCheckpointIndex(0);
    setSelectedAnswer(null);
    setFeedback(null);
    setHintVisible(false);
    setAnswerRevealed(false);
    setCheckpointAnswered(false);
    setSandboxValues([...inputValues]);
    setSandboxResult(null);
    setActivityLog([]);
    addLogEntry('Session reset. All state cleared.');
  };

  // Render linked list visualization
  const renderLinkedList = () => {
    const values = currentTrace.listSnapshot;
    if (!values || values.length === 0) {
      return <span className="ll-empty">(empty list)</span>;
    }

    return (
      <div className="ll-container">
        {values.map((val, idx) => {
          let nodeClass = 'll-node';
          if (val === currentTrace.prev) nodeClass += ' ll-node-prev';
          if (val === currentTrace.curr) nodeClass += ' ll-node-curr';
          if (val === currentTrace.next) nodeClass += ' ll-node-next';

          return (
            <React.Fragment key={idx}>
              <div className={nodeClass}>
                <span className="ll-node-val">{val}</span>
              </div>
              {idx < values.length - 1 && (
                <div className="ll-arrow">
                  <svg width="40" height="20" viewBox="0 0 40 20">
                    <line x1="0" y1="10" x2="30" y2="10" stroke="#94a3b8" strokeWidth="2" />
                    <polygon points="30,5 40,10 30,15" fill="#94a3b8" />
                  </svg>
                </div>
              )}
            </React.Fragment>
          );
        })}
        <div className="ll-null-marker">
          <span>null</span>
        </div>
      </div>
    );
  };

  // Render pointer state boxes
  const renderPointerState = () => {
    const pointers = [
      { label: 'prev', value: currentTrace.prev, color: 'var(--color-node-prev)' },
      { label: 'curr', value: currentTrace.curr, color: 'var(--color-node-curr)' },
      { label: 'next', value: currentTrace.next, color: 'var(--color-node-next)' }
    ];

    return (
      <div className="pointer-state">
        {pointers.map(p => (
          <div key={p.label} className="pointer-box" style={{ borderColor: p.color }}>
            <span className="pointer-label" style={{ color: p.color }}>{p.label}</span>
            <span className="pointer-value">{p.value !== null ? p.value : 'null'}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="12" width="12" height="24" rx="3" fill="#6366f1" stroke="#4f46e5" strokeWidth="1.5" />
            <rect x="32" y="12" width="12" height="24" rx="3" fill="#6366f1" stroke="#4f46e5" strokeWidth="1.5" />
            <rect x="18" y="20" width="12" height="8" rx="2" fill="#f59e0b" stroke="#d97706" strokeWidth="1.5" />
            <path d="M24 16V20" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
            <path d="M24 28V32" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
            <path d="M16 18L24 18" stroke="#a78bfa" strokeWidth="1.5" strokeLinecap="round" markerEnd="url(#arrowLeft)" />
            <path d="M32 30L24 30" stroke="#a78bfa" strokeWidth="1.5" strokeLinecap="round" markerEnd="url(#arrowRight)" />
            <defs>
              <marker id="arrowLeft" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse">
                <path d="M0,0 L6,3 L0,6 Z" fill="#a78bfa" />
              </marker>
              <marker id="arrowRight" markerWidth="6" markerHeight="6" refX="1" refY="3" orient="auto">
                <path d="M6,0 L0,3 L6,6 Z" fill="#a78bfa" />
              </marker>
            </defs>
          </svg>
        </div>
        <h1>Reverse Linked List</h1>
        <p className="subtitle">Algorithm Family: Linked List and Cache</p>
      </header>

      <main className="app-main">
        {/* Problem Section */}
        <section className="card problem-card">
          <h2>Problem Statement</h2>
          <p>
            Suppose you are developing a browser where a user visits a series of web pages,
            and a list <code>values</code> records the visited URL IDs. The browser needs to
            generate a backward history path, i.e., reverse the visit order so that the user
            can gradually go back from the current page to the earliest visited page.
            Given the list <code>values</code> representing the visited page IDs in order,
            please implement an algorithm that returns the reversed list, i.e., the backward order.
          </p>

          <div className="io-display">
            <div className="io-box">
              <h3>Concrete Input (JSON)</h3>
              <pre className="code-block"><code>{highlightJSON(inputJSON)}</code></pre>
            </div>
            <div className="io-divider" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <path d="M6 16H26" stroke="#4a6cf7" strokeWidth="2.5" strokeLinecap="round" />
                <polygon points="20,10 27,16 20,22" fill="#4a6cf7" />
              </svg>
            </div>
            <div className="io-box">
              <h3>Expected Final Answer (JSON)</h3>
              <pre className="code-block answer-block"><code>{highlightJSON(outputJSON)}</code></pre>
            </div>
          </div>
        </section>

        {/* Visualization Section */}
        <section className="card viz-card">
          <h2>Step-by-Step Visualization</h2>
          <p className="step-indicator">
            Step {currentTrace.step} of {steps.length - 1}
            {currentTrace.isComplete ? ' — Algorithm Complete' : ''}
          </p>

          <div className="viz-area">
            <div className="list-display">
              <h3>Current List State</h3>
              {renderLinkedList()}
            </div>

            <div className="pointer-display">
              <h3>Pointer State</h3>
              {renderPointerState()}
            </div>
          </div>

          <p className="step-description">{currentTrace.description}</p>

          <div className="viz-controls">
            <button
              className="btn btn-secondary"
              onClick={() => handleStepChange(-1)}
              disabled={currentStep === 0}
              aria-label="Go to previous step"
            >
              ← Previous Step
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleStepChange(1)}
              disabled={currentStep >= steps.length - 1}
              aria-label="Go to next step"
            >
              Next Step →
            </button>
            <button
              className="btn btn-outline"
              onClick={() => { setCurrentStep(0); addLogEntry('Jumped to initial state.'); }}
              aria-label="Reset visualization to start"
            >
              Reset to Start
            </button>
          </div>

          <div className="legend">
            <span className="legend-item"><span className="legend-dot" style={{ background: 'var(--color-node-prev)' }}></span> prev</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: 'var(--color-node-curr)' }}></span> curr</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: 'var(--color-node-next)' }}></span> next</span>
          </div>
        </section>

        {/* Checkpoint Section */}
        <section className="card checkpoint-card">
          <h2>Checkpoint {checkpointIndex + 1} of {CHECKPOINTS.length}</h2>
          <p className="checkpoint-question">{currentCheckpoint.question}</p>

          <div className="options-list">
            {currentCheckpoint.options.map((opt, idx) => (
              <label
                key={idx}
                className={`option-label ${selectedAnswer === idx ? 'option-selected' : ''} ${answerRevealed && idx === currentCheckpoint.correctIndex ? 'option-correct-reveal' : ''} ${checkpointAnswered && selectedAnswer === idx && selectedAnswer !== currentCheckpoint.correctIndex ? 'option-incorrect' : ''}`}
              >
                <input
                  type="radio"
                  name="checkpoint-answer"
                  value={idx}
                  checked={selectedAnswer === idx}
                  onChange={() => handleAnswerSelect(idx)}
                  disabled={checkpointAnswered}
                  aria-label={`Option ${idx + 1}: ${opt}`}
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>

          <div className="checkpoint-actions">
            <button
              className="btn btn-primary"
              onClick={handleSubmitAnswer}
              disabled={selectedAnswer === null || checkpointAnswered}
              aria-label="Submit your answer"
            >
              Submit Answer
            </button>
            <button
              className="btn btn-outline"
              onClick={handleShowHint}
              disabled={checkpointAnswered}
              aria-label="Show a hint"
            >
              Hint
            </button>
            <button
              className="btn btn-outline"
              onClick={handleShowAnswer}
              disabled={checkpointAnswered}
              aria-label="Reveal the correct answer"
            >
              Show Answer
            </button>
            {checkpointAnswered && checkpointIndex < CHECKPOINTS.length - 1 && (
              <button className="btn btn-primary" onClick={handleNextCheckpoint} aria-label="Go to next checkpoint">
                Next Checkpoint →
              </button>
            )}
          </div>

          {hintVisible && !checkpointAnswered && (
            <div className="feedback hint-feedback" role="status">
              <strong>Hint:</strong> {currentCheckpoint.hint}
            </div>
          )}

          {feedback && (
            <div className={`feedback ${feedback.type === 'correct' ? 'feedback-correct' : 'feedback-incorrect'}`} role="alert">
              <strong>{feedback.type === 'correct' ? '✓ Correct!' : '✗ Incorrect'}</strong>
              <p>{feedback.message}</p>
            </div>
          )}
        </section>

        {/* Sandbox Section */}
        <section className="card sandbox-card">
          <h2>Sandbox: Experiment with Values</h2>
          <p>Modify the list values below and see how the reversal result changes.</p>

          <div className="sandbox-list">
            {sandboxValues.map((val, idx) => (
              <div key={idx} className="sandbox-node-row">
                <span className="sandbox-index">[{idx}]</span>
                <input
                  type="number"
                  className="sandbox-input"
                  value={val}
                  onChange={(e) => handleSandboxChange(idx, e.target.value)}
                  aria-label={`Node value at index ${idx}`}
                />
                <button
                  className="btn btn-sm btn-danger-outline"
                  onClick={() => handleSandboxRemove(idx)}
                  disabled={sandboxValues.length <= 1}
                  aria-label={`Remove node at index ${idx}`}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="sandbox-actions">
            <button className="btn btn-outline" onClick={handleSandboxAdd} aria-label="Add a new node">
              + Add Node
            </button>
            <button className="btn btn-primary" onClick={handleSandboxReverse} aria-label="Reverse the sandbox list">
              Reverse List
            </button>
          </div>

          {sandboxResult && (
            <div className="sandbox-result">
              <strong>Reversed Result:</strong>
              <pre className="code-block">{highlightJSON(JSON.stringify(sandboxResult, null, 2))}</pre>
            </div>
          )}
        </section>

        {/* Learning Objectives */}
        <section className="card objectives-card">
          <h2>Learning Objectives</h2>
          <ul className="objectives-list">
            <li>Understand the state changes of the three pointers prev, curr, and next in iterative reversal of a singly linked list.</li>
            <li>Predict the next pointer direction based on the trace and explain the reason.</li>
            <li>Identify invariants of linked list node connections during the reversal process, and use them for debugging.</li>
          </ul>
        </section>

        {/* Activity Log */}
        <section className="card log-card">
          <h2>Learning Activity Log</h2>
          <div className="log-container" ref={logRef}>
            {activityLog.length === 0 ? (
              <p className="log-empty">No activities recorded yet. Interact with the page to see your learning log.</p>
            ) : (
              <ul className="log-list">
                {activityLog.map(entry => (
                  <li key={entry.id} className="log-entry">
                    <span className="log-time">[{entry.timestamp}]</span>
                    <span className="log-msg">{entry.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button className="btn btn-outline btn-sm" onClick={handleReset} style={{ marginTop: '12px' }} aria-label="Reset entire session">
            Reset Session
          </button>
        </section>
      </main>

      <footer className="app-footer">
        <p>Reverse Linked List — Interactive Algorithm Learning Tool</p>
      </footer>
    </div>
  );
}

export default App;
