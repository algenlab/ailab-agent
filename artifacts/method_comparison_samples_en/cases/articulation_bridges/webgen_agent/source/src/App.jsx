import React, { useState, useReducer, useCallback, useRef, useEffect } from 'react';
import {
  graphData,
  graphDataModified,
  originalSteps,
  modifiedSteps,
  checkpointQuestions,
} from './algorithmData';

// --- JSON syntax highlighter ---
function highlightJSON(jsonStr) {
  // Tokenize a JSON string into colored spans
  const tokens = [];
  let i = 0;
  const len = jsonStr.length;

  while (i < len) {
    const ch = jsonStr[i];

    // String (key or value)
    if (ch === '"') {
      let j = i + 1;
      let esc = false;
      while (j < len) {
        if (esc) { esc = false; j++; continue; }
        if (jsonStr[j] === '\\') { esc = true; j++; continue; }
        if (jsonStr[j] === '"') break;
        j++;
      }
      const full = jsonStr.substring(i, j + 1);

      // Determine if it's a key (followed by colon after optional whitespace)
      let after = jsonStr.substring(j + 1).trimStart();
      if (after.startsWith(':')) {
        tokens.push({ t: 'key', v: full });
      } else {
        tokens.push({ t: 'string', v: full });
      }
      i = j + 1;
      continue;
    }

    // Number
    if ((ch >= '0' && ch <= '9') || ch === '-') {
      let j = i;
      while (j < len && /[0-9.\-+eE]/.test(jsonStr[j])) j++;
      tokens.push({ t: 'number', v: jsonStr.substring(i, j) });
      i = j;
      continue;
    }

    // Brackets and braces
    if ('{}[]'.includes(ch)) {
      tokens.push({ t: 'bracket', v: ch });
      i++;
      continue;
    }

    // Colon
    if (ch === ':') {
      tokens.push({ t: 'colon', v: ch });
      i++;
      continue;
    }

    // Comma
    if (ch === ',') {
      tokens.push({ t: 'comma', v: ch });
      i++;
      continue;
    }

    // Whitespace
    if (/\s/.test(ch)) {
      let j = i;
      while (j < len && /\s/.test(jsonStr[j])) j++;
      tokens.push({ t: 'ws', v: jsonStr.substring(i, j) });
      i = j;
      continue;
    }

    // Literals: true, false, null
    if (/[a-z]/.test(ch)) {
      let j = i;
      while (j < len && /[a-z]/.test(jsonStr[j])) j++;
      tokens.push({ t: 'literal', v: jsonStr.substring(i, j) });
      i = j;
      continue;
    }

    // Fallback
    tokens.push({ t: 'plain', v: ch });
    i++;
  }

  return tokens.map((tok, idx) => {
    const cls = {
      key: 'json-key',
      string: 'json-string',
      number: 'json-number',
      bracket: 'json-bracket',
      colon: 'json-colon',
      comma: 'json-plain',
      ws: 'json-ws',
      literal: 'json-literal',
      plain: 'json-plain',
    }[tok.t] || 'json-plain';
    return <span key={idx} className={cls}>{tok.v}</span>;
  });
}

// --- Reducer for algorithm simulation ---
const initialState = {
  stepIndex: 0,
  useModifiedGraph: false,
  // Checkpoint state
  activeCheckpoint: null,
  checkpointAnswered: false,
  // Log
  logEntries: [],
  // Draggable node positions
  nodePositions: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STEP': {
      const steps = state.useModifiedGraph ? modifiedSteps : originalSteps;
      const newIndex = Math.max(0, Math.min(action.payload, steps.length - 1));
      return { ...state, stepIndex: newIndex };
    }
    case 'NEXT_STEP': {
      const steps = state.useModifiedGraph ? modifiedSteps : originalSteps;
      if (state.stepIndex >= steps.length - 1) return state;
      const nextIndex = state.stepIndex + 1;
      const cq = checkpointQuestions.find((q) => q.triggerStepIndex === nextIndex);
      return {
        ...state,
        stepIndex: nextIndex,
        activeCheckpoint: cq ? { questionObj: cq, answered: false, correct: false, selectedOption: null } : null,
        checkpointAnswered: false,
      };
    }
    case 'PREV_STEP': {
      if (state.stepIndex <= 0) return state;
      return { ...state, stepIndex: state.stepIndex - 1, activeCheckpoint: null, checkpointAnswered: false };
    }
    case 'TOGGLE_MODIFIED': {
      const newModified = !state.useModifiedGraph;
      return {
        ...state,
        useModifiedGraph: newModified,
        stepIndex: 0,
        activeCheckpoint: null,
        checkpointAnswered: false,
        logEntries: [
          ...state.logEntries,
          {
            time: new Date().toLocaleTimeString(),
            icon: '\u{1F504}',
            message: newModified
              ? 'Switched to modified graph (added edge C-E).'
              : 'Switched back to original graph.',
          },
        ],
      };
    }
    case 'ANSWER_CHECKPOINT': {
      if (!state.activeCheckpoint || state.checkpointAnswered) return state;
      const isCorrect = action.payload === state.activeCheckpoint.questionObj.correctAnswer;
      const quiz = state.activeCheckpoint.questionObj;
      const chosenLabel = quiz.options.find((o) => o.id === action.payload)?.text || action.payload;
      return {
        ...state,
        checkpointAnswered: true,
        activeCheckpoint: {
          ...state.activeCheckpoint,
          answered: true,
          correct: isCorrect,
          selectedOption: action.payload,
        },
        logEntries: [
          ...state.logEntries,
          {
            time: new Date().toLocaleTimeString(),
            icon: isCorrect ? '\u2705' : '\u274C',
            message: isCorrect
              ? `Checkpoint Q${quiz.id}: Correct! "${chosenLabel}"`
              : `Checkpoint Q${quiz.id}: Incorrect. You chose "${chosenLabel}".`,
            type: isCorrect ? 'correct-log' : 'incorrect-log',
          },
        ],
      };
    }
    case 'SHOW_HINT': {
      if (!state.activeCheckpoint) return state;
      const quiz = state.activeCheckpoint.questionObj;
      return {
        ...state,
        logEntries: [
          ...state.logEntries,
          {
            time: new Date().toLocaleTimeString(),
            icon: '\u{1F4A1}',
            message: `Hint for Q${quiz.id}: The correct answer is option "${quiz.correctAnswer}".`,
            type: 'hint-log',
          },
        ],
      };
    }
    case 'SHOW_ANSWER': {
      if (!state.activeCheckpoint) return state;
      const quiz = state.activeCheckpoint.questionObj;
      const correctOpt = quiz.options.find((o) => o.id === quiz.correctAnswer);
      return {
        ...state,
        checkpointAnswered: true,
        activeCheckpoint: {
          ...state.activeCheckpoint,
          answered: true,
          correct: true,
          selectedOption: quiz.correctAnswer,
        },
        logEntries: [
          ...state.logEntries,
          {
            time: new Date().toLocaleTimeString(),
            icon: '\u{1F441}\uFE0F',
            message: `Show Answer Q${quiz.id}: "${correctOpt?.text || ''}" \u2014 ${quiz.explanation}`,
            type: 'hint-log',
          },
        ],
      };
    }
    case 'DISMISS_CHECKPOINT': {
      return { ...state, activeCheckpoint: null, checkpointAnswered: false };
    }
    case 'ADD_LOG': {
      return {
        ...state,
        logEntries: [...state.logEntries, action.payload],
      };
    }
    case 'UPDATE_NODE_POSITION': {
      const currentPositions = state.nodePositions || { ...graphData.nodes };
      return {
        ...state,
        nodePositions: {
          ...currentPositions,
          [action.payload.node]: { x: action.payload.x, y: action.payload.y },
        },
      };
    }
    case 'RESET': {
      return { ...initialState };
    }
    default:
      return state;
  }
}

// --- Helper: Get step data ---
function getStepData(state) {
  const steps = state.useModifiedGraph ? modifiedSteps : originalSteps;
  return steps[state.stepIndex] || steps[0];
}

// --- Graph Visualization Component ---
function GraphVisualization({ stepData, useModifiedGraph, nodePositions, onNodeMove }) {
  const baseGraph = useModifiedGraph ? graphDataModified : graphData;
  const graph = {
    ...baseGraph,
    nodes: nodePositions || baseGraph.nodes,
  };
  const { highlightEdge, highlightNode, bridges: stepBridges, articulations: stepArticulations } = stepData;
  const svgRef = useRef(null);
  const dragRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const viewBoxWidth = 540;
  const viewBoxHeight = 320;

  const isBridge = (edge) => {
    const [u, v] = edge;
    return stepBridges.some((b) => (b[0] === u && b[1] === v) || (b[0] === v && b[1] === u));
  };

  const isHighlightEdge = (edge) => {
    if (!highlightEdge) return false;
    const [u, v] = edge;
    return (highlightEdge[0] === u && highlightEdge[1] === v) || (highlightEdge[0] === v && highlightEdge[1] === u);
  };

  const isBackEdge = (edge) => {
    return stepData.type === 'backedge' && isHighlightEdge(edge);
  };

  const isExtraEdge = (edge) => {
    if (!useModifiedGraph) return false;
    return (edge[0] === 'C' && edge[1] === 'E') || (edge[0] === 'E' && edge[1] === 'C');
  };

  const getNodeClass = (node) => {
    const classes = [];
    if (stepArticulations.includes(node)) classes.push('articulation');
    if (highlightNode === node) classes.push('current');
    else if (stepData.visited && stepData.visited.has(node)) classes.push('visited');
    return classes.join(' ');
  };

  const getNodeTooltip = (node) => {
    const { dfn, low, parent } = stepData;
    const parts = [`Node ${node}`];
    if (dfn[node] !== undefined) parts.push(`dfn=${dfn[node]}`);
    if (low[node] !== undefined) parts.push(`low=${low[node]}`);
    if (parent[node] !== undefined) parts.push(`parent=${parent[node] || 'null'}`);
    if (stepArticulations.includes(node)) parts.push('AP');
    return parts.join(' \u2022 ');
  };

  const handleMouseDown = (e, nodeName) => {
    e.preventDefault();
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const pt = svgEl.createSVGPoint();
    const getCoords = (ev) => {
      pt.x = ev.clientX;
      pt.y = ev.clientY;
      return pt.matrixTransform(svgEl.getScreenCTM().inverse());
    };

    const startCoords = getCoords(e);
    const startPos = graph.nodes[nodeName] || { x: 0, y: 0 };
    dragRef.current = { nodeName, startCoords, startPos };

    const handleMove = (ev) => {
      if (!dragRef.current) return;
      const currentCoords = getCoords(ev);
      const dx = currentCoords.x - dragRef.current.startCoords.x;
      const dy = currentCoords.y - dragRef.current.startCoords.y;
      const newX = Math.max(25, Math.min(viewBoxWidth - 25, dragRef.current.startPos.x + dx));
      const newY = Math.max(25, Math.min(viewBoxHeight - 25, dragRef.current.startPos.y + dy));
      onNodeMove(dragRef.current.nodeName, newX, newY);
    };

    const handleUp = () => {
      dragRef.current = null;
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
  };

  const handleMouseEnter = (e, nodeName) => {
    const rect = e.target.getBoundingClientRect();
    setTooltip({
      node: nodeName,
      x: rect.left + rect.width / 2,
      y: rect.top - 6,
    });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
    if (dragRef.current) {
      dragRef.current = null;
    }
  };

  return (
    <div className="graph-container">
      <svg className="graph-svg" viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`} xmlns="http://www.w3.org/2000/svg" ref={svgRef}>
        {graph.edges.map((edge, i) => {
          const [u, v] = edge;
          const from = graph.nodes[u];
          const to = graph.nodes[v];
          if (!from || !to) return null;
          let className = 'graph-edge';
          if (isBridge(edge)) className += ' bridge';
          else if (isHighlightEdge(edge) && stepData.type === 'backtrack') className += ' highlight';
          else if (isBackEdge(edge)) className += ' backedge';
          else if (isHighlightEdge(edge)) className += ' highlight';
          if (isExtraEdge(edge)) className += ' extra-edge';
          return (
            <line
              key={`edge-${i}`}
              className={className}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
            />
          );
        })}
        {Object.entries(graph.nodes).map(([name, pos]) => (
          <g
            key={`node-${name}`}
            className="graph-node-group"
            onMouseDown={(e) => handleMouseDown(e, name)}
            onMouseEnter={(e) => handleMouseEnter(e, name)}
            onMouseLeave={handleMouseLeave}
          >
            <circle
              className={`graph-node-circle ${getNodeClass(name)}`}
              cx={pos.x}
              cy={pos.y}
              r={highlightNode === name ? 21 : 19}
            />
            <text className="graph-node-label" x={pos.x} y={pos.y}>
              {name}
            </text>
            {stepArticulations.includes(name) && (
              <text className="articulation-marker" x={pos.x} y={pos.y + 26}>
                {'\u26A1'}AP
              </text>
            )}
          </g>
        ))}
        {stepBridges.map((bridge, i) => {
          const [u, v] = bridge;
          const from = graph.nodes[u];
          const to = graph.nodes[v];
          if (!from || !to) return null;
          const mx = (from.x + to.x) / 2;
          const my = (from.y + to.y) / 2 - 9;
          return (
            <text
              key={`bridge-label-${i}`}
              x={mx}
              y={my}
              fill="#ef4444"
              fontSize="10"
              fontWeight="700"
              textAnchor="middle"
              pointerEvents="none"
            >
              {'\uD83C\uDF09'}
            </text>
          );
        })}
      </svg>
      {tooltip && (
        <div
          className="node-tooltip"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translate(-50%, -100%)',
            position: 'fixed',
          }}
        >
          {getNodeTooltip(tooltip.node)}
        </div>
      )}
    </div>
  );
}

// --- Algorithm State Table ---
function StateTable({ stepData }) {
  const nodes = ['A', 'B', 'C', 'D', 'E'];
  const { dfn, low, parent, highlightNode, lowUpdated } = stepData;
  const updatedNode = lowUpdated?.node;

  const hasAnyValue = nodes.some((n) => dfn[n] !== undefined || low[n] !== undefined || parent[n] !== undefined);

  const renderCell = (node, value, isHighlighted, isUpdated) => {
    if (value === undefined) {
      const cls = hasAnyValue ? 'empty-init' : '';
      return <td className={cls}>{hasAnyValue ? '\u2014' : '\u00B7'}</td>;
    }
    let cls = 'has-value';
    if (isHighlighted) cls += ' highlight-cell';
    if (isUpdated) cls += ' updated-cell';
    return <td className={cls}>{value}</td>;
  };

  return (
    <table className="state-table" role="table" aria-label="Algorithm state table showing dfn, low, and parent values for each node">
      <thead>
        <tr>
          <th>Node</th>
          {nodes.map((n) => (
            <th key={n}>{n}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>dfn</strong></td>
          {nodes.map((n) =>
            renderCell(n, dfn[n], highlightNode === n && stepData.type === 'visit', false)
          )}
        </tr>
        <tr>
          <td><strong>low</strong></td>
          {nodes.map((n) =>
            renderCell(n, low[n], highlightNode === n && stepData.type !== 'visit', updatedNode === n)
          )}
        </tr>
        <tr>
          <td><strong>parent</strong></td>
          {nodes.map((n) =>
            renderCell(n, parent[n] !== undefined ? parent[n] : undefined, false, false)
          )}
        </tr>
      </tbody>
    </table>
  );
}

// --- Checkpoint Quiz Component ---
function CheckpointQuiz({ checkpoint, onAnswer, onHint, onShowAnswer, onDismiss, answered, selectedOption, correct }) {
  const [selected, setSelected] = useState(selectedOption || null);

  useEffect(() => {
    setSelected(selectedOption || null);
  }, [selectedOption, checkpoint?.questionObj?.id]);

  if (!checkpoint) return null;

  const quiz = checkpoint.questionObj;

  const handleSelect = (optionId) => {
    if (answered) return;
    setSelected(optionId);
  };

  const handleSubmit = () => {
    if (!selected || answered) return;
    onAnswer(selected);
  };

  return (
    <div className="checkpoint-overlay" role="region" aria-label={`Checkpoint question ${quiz.id}`}>
      <h4>{'\uD83D\uDCCB'} Checkpoint Question #{quiz.id}</h4>
      <p className="checkpoint-question">{quiz.question}</p>
      <ul className="option-list" role="radiogroup" aria-label="Answer options">
        {quiz.options.map((opt) => {
          let cls = 'option-item';
          if (answered && opt.id === quiz.correctAnswer) cls += ' correct';
          else if (answered && opt.id === selected && opt.id !== quiz.correctAnswer) cls += ' incorrect';
          else if (opt.id === selected) cls += ' selected';
          return (
            <li key={opt.id} className={cls} onClick={() => handleSelect(opt.id)} role="radio" aria-checked={opt.id === selected}>
              <input
                type="radio"
                className="option-radio"
                name={`checkpoint-${quiz.id}`}
                checked={opt.id === selected}
                onChange={() => handleSelect(opt.id)}
                disabled={answered}
                aria-label={opt.text}
              />
              <span>{opt.text}</span>
            </li>
          );
        })}
      </ul>
      {answered && (
        <div className={`feedback-box ${correct ? 'correct' : 'incorrect'}`} role="alert">
          {correct ? '\u2705 Correct! ' : '\u274C Incorrect. '}
          {quiz.explanation}
        </div>
      )}
      <div className="quiz-actions">
        {!answered && (
          <>
            <button className="step-btn primary" onClick={handleSubmit} disabled={!selected} aria-label="Submit your answer">
              Submit Answer
            </button>
            <button className="step-btn" onClick={onHint} aria-label="Show a hint">
              {'\uD83D\uDCA1'} Hint
            </button>
            <button className="step-btn" onClick={onShowAnswer} aria-label="Reveal the correct answer">
              {'\uD83D\uDC41\uFE0F'} Show Answer
            </button>
          </>
        )}
        {answered && (
          <button className="step-btn primary" onClick={onDismiss} aria-label="Continue to next step">
            Continue {'\u2192'}
          </button>
        )}
      </div>
    </div>
  );
}

// --- Learning Log Component ---
function LearningLog({ entries }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [entries.length]);

  return (
    <div className="learning-log" ref={logRef} role="log" aria-label="Activity log">
      {entries.length === 0 && (
        <div className="log-entry">
          <span className="log-icon">{'\uD83D\uDCDD'}</span>
          <span className="log-message">Activity log is empty. Interact with the simulation to see entries here.</span>
        </div>
      )}
      {entries.map((entry, i) => (
        <div key={i} className="log-entry">
          <span className="log-time">{entry.time}</span>
          <span className="log-icon">{entry.icon}</span>
          <span className={`log-message ${entry.type || ''}`}>{entry.message}</span>
        </div>
      ))}
    </div>
  );
}

// --- Main App Component ---
export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const stepData = getStepData(state);
  const steps = state.useModifiedGraph ? modifiedSteps : originalSteps;
  const logEntriesRef = useRef({});

  useEffect(() => {
    const entry = {
      time: new Date().toLocaleTimeString(),
      icon: '\uD83D\uDCCD',
      message: `Step ${state.stepIndex + 1}/${steps.length}: ${stepData.description}`,
    };
    if (logEntriesRef.current.lastStep !== state.stepIndex) {
      logEntriesRef.current.lastStep = state.stepIndex;
      dispatch({ type: 'ADD_LOG', payload: entry });
    }
  }, [state.stepIndex, state.useModifiedGraph]);

  const handleAnswer = useCallback(
    (optionId) => {
      dispatch({ type: 'ANSWER_CHECKPOINT', payload: optionId });
    },
    []
  );

  const handleHint = useCallback(() => {
    dispatch({ type: 'SHOW_HINT' });
  }, []);

  const handleShowAnswer = useCallback(() => {
    dispatch({ type: 'SHOW_ANSWER' });
  }, []);

  const handleDismissCheckpoint = useCallback(() => {
    dispatch({ type: 'DISMISS_CHECKPOINT' });
  }, []);

  const handleReset = useCallback(() => {
    dispatch({ type: 'RESET' });
    logEntriesRef.current = {};
  }, []);

  const handleNodeMove = useCallback((node, x, y) => {
    dispatch({ type: 'UPDATE_NODE_POSITION', payload: { node, x, y } });
  }, []);

  const finalAnswer = state.useModifiedGraph
    ? { articulation: ['B'], bridges: [['A', 'B']] }
    : { articulation: ['B', 'D'], bridges: [['D', 'E'], ['A', 'B']] };

  const inputJSON = JSON.stringify({ graph: graphData.adjacency }, null, 2);
  const expectedJSON = JSON.stringify(
    { articulation: ['B', 'D'], bridges: [['D', 'E'], ['A', 'B']] },
    null,
    2
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>Articulation Points and Bridges</h1>
        <p className="subtitle">Advanced Graph Algorithms — DFS, dfn/low Arrays, and Critical Edge Detection</p>
      </header>

      <div className="main-content">
        {/* Left Column */}
        <div className="left-column" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div className="panel">
            <div className="panel-title">Graph Visualization</div>
            <GraphVisualization
              stepData={stepData}
              useModifiedGraph={state.useModifiedGraph}
              nodePositions={state.nodePositions}
              onNodeMove={handleNodeMove}
            />
            <div className="modifier-section">
              <label className="toggle-switch" aria-label="Toggle edge C-E on the graph">
                <input
                  type="checkbox"
                  checked={state.useModifiedGraph}
                  onChange={() => dispatch({ type: 'TOGGLE_MODIFIED' })}
                />
                <span className="toggle-slider"></span>
              </label>
              <span>
                {state.useModifiedGraph
                  ? 'Edge (C,E) added — observe changes'
                  : 'Add edge (C,E) to modify the graph'}
              </span>
            </div>
            <div className="results-display">
              <span className="result-badge articulation-badge">
                Articulation Points: [{finalAnswer.articulation.join(', ') || 'none'}]
              </span>
              <span className="result-badge bridge-badge">
                Bridges: [{finalAnswer.bridges.map((b) => `(${b[0]},${b[1]})`).join(', ') || 'none'}]
              </span>
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">Algorithm State (dfn / low / parent)</div>
            <StateTable stepData={stepData} />
          </div>

          <div className="step-description" aria-live="polite">{stepData.description}</div>

          <div className="step-controls" role="toolbar" aria-label="Step navigation controls">
            <button
              className="step-btn"
              onClick={() => dispatch({ type: 'PREV_STEP' })}
              disabled={state.stepIndex <= 0}
              aria-label="Go to previous step"
            >
              {'\u25C0'} Prev
            </button>
            <button
              className="step-btn primary"
              onClick={() => dispatch({ type: 'NEXT_STEP' })}
              disabled={state.stepIndex >= steps.length - 1}
              aria-label="Go to next step"
            >
              Next {'\u25B6'}
            </button>
            <button className="step-btn" onClick={handleReset} aria-label="Reset simulation to beginning">
              {'\u21BA'} Reset
            </button>
            <span className="step-indicator">
              Step {state.stepIndex + 1} / {steps.length}
            </span>
            <input
              type="range"
              className="step-slider"
              min={0}
              max={steps.length - 1}
              value={state.stepIndex}
              onChange={(e) => dispatch({ type: 'SET_STEP', payload: parseInt(e.target.value) })}
              aria-label="Step progress slider"
            />
          </div>

          <CheckpointQuiz
            checkpoint={state.activeCheckpoint}
            onAnswer={handleAnswer}
            onHint={handleHint}
            onShowAnswer={handleShowAnswer}
            onDismiss={handleDismissCheckpoint}
            answered={state.checkpointAnswered}
            selectedOption={state.activeCheckpoint?.selectedOption}
            correct={state.activeCheckpoint?.correct}
          />
        </div>

        {/* Right Column */}
        <div className="right-column" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="panel problem-panel">
            <div className="panel-title">Problem Description</div>
            <p className="desc-text">
              In a city's communication network, each exchange station is a <strong>node</strong> and each fiber connection is an <strong>undirected edge</strong>. Find all <strong>articulation points</strong> (critical stations) and <strong>bridges</strong> (critical fibers).
            </p>
            <div className="io-label">Input (Adjacency List):</div>
            <div className="io-block" tabIndex={0} role="region" aria-label="Graph input as JSON adjacency list">
              {highlightJSON(inputJSON)}
            </div>
            <div className="io-label">Expected Answer:</div>
            <div className="io-block expected-answer" tabIndex={0} role="region" aria-label="Expected final answer as JSON">
              {highlightJSON(expectedJSON)}
            </div>
            <p className="strategy-text">
              <strong>Strategy:</strong> DFS maintains <code>dfn</code> (discovery time), <code>low</code> (lowest reachable ancestor), and <code>parent</code> arrays.
              <br />
              • <strong>Bridge:</strong> <code>low[child] > dfn[u]</code>
              <br />
              • <strong>Articulation point:</strong> <code>low[child] ≥ dfn[u]</code> (non-root) or root with ≥2 children
            </p>
          </div>

          <div className="panel">
            <div className="panel-title">Learning Objectives</div>
            <ul className="objectives-list">
              <li>Master the update rules of <code>dfn</code> and <code>low</code> arrays during backtracking</li>
              <li>Predict the next node to be explored by DFS based on current dfn/low states</li>
              <li>Understand the difference between <code>low[child] > dfn[u]</code> and <code>low[child] ≥ dfn[u]</code></li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-title">Activity Log</div>
            <LearningLog entries={state.logEntries} />
          </div>
        </div>
      </div>
    </div>
  );
}
