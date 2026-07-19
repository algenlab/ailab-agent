import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import TreeVisualization from './components/TreeVisualization';
import DpTable from './components/DpTable';
import StepControls from './components/StepControls';
import CheckpointPanel from './components/CheckpointPanel';
import LearningLog from './components/LearningLog';
import JsonDisplay from './components/JsonDisplay';

// ---------- Input Data ----------
const INPUT_DATA = {
  tree: {
    edges: [["1","2"], ["1","3"], ["2","4"], ["2","5"]],
    nodes: [
      { id: "1", value: 3 },
      { id: "2", value: 2 },
      { id: "3", value: 1 },
      { id: "4", value: 10 },
      { id: "5", value: 1 }
    ]
  }
};
const EXPECTED_FINAL_ANSWER = 14;

// ---------- Algorithm Step Computer ----------
function computeAlgorithmSteps(inputData) {
  const { nodes, edges } = inputData.tree;
  const valueMap = {};
  const adj = {};
  nodes.forEach(n => {
    valueMap[n.id] = n.value;
    adj[n.id] = [];
  });
  edges.forEach(([u, v]) => {
    adj[u].push(v);
    adj[v].push(u);
  });

  const root = nodes[0].id;
  const parentMap = {};
  const order = [];
  const visited = new Set();
  function dfs(node, parent) {
    visited.add(node);
    parentMap[node] = parent;
    adj[node].forEach(neighbor => {
      if (neighbor !== parent && !visited.has(neighbor)) {
        dfs(neighbor, node);
      }
    });
    order.push(node);
  }
  dfs(root, null);

  const dpTake = {};
  const dpSkip = {};
  const stepResults = [];

  stepResults.push({
    type: 'start',
    description: 'Initial tree loaded. We will compute DP bottom-up using postorder traversal.',
    processedNodes: [],
    currentProcessing: null
  });

  order.forEach((node, idx) => {
    const children = adj[node].filter(child => child !== parentMap[node]);
    const childrenStates = children.map(child => ({
      id: child,
      dpTake: dpTake[child],
      dpSkip: dpSkip[child],
      value: valueMap[child]
    }));

    const take = valueMap[node] + children.reduce((sum, child) => sum + dpSkip[child], 0);
    const skip = children.reduce((sum, child) => sum + Math.max(dpTake[child], dpSkip[child]), 0);
    dpTake[node] = take;
    dpSkip[node] = skip;

    stepResults.push({
      type: 'compute',
      nodeId: node,
      nodeValue: valueMap[node],
      childrenStates,
      dpTake: take,
      dpSkip: skip,
      isRoot: node === root,
      processedSoFar: order.slice(0, idx + 1),
      currentProcessing: node,
      formulaTake: `dp_take[${node}] = value[${node}] + sum(dp_skip of children) = ${valueMap[node]} + ${children.map(c => `dp_skip[${c.id}]=${dpSkip[c.id]}`).join(' + ') || '0'} = ${take}`,
      formulaSkip: `dp_skip[${node}] = sum(max(dp_take[child], dp_skip[child])) = ${children.map(c => `max(${dpTake[c.id]}, ${dpSkip[c.id]})=${Math.max(dpTake[c.id], dpSkip[c.id])}`).join(' + ') || '0'} = ${skip}`
    });
  });

  const finalAnswer = Math.max(dpTake[root], dpSkip[root]);
  stepResults.push({
    type: 'final',
    description: `Algorithm complete. Final answer: max(dp_take[${root}], dp_skip[${root}]) = max(${dpTake[root]}, ${dpSkip[root]}) = ${finalAnswer}.`,
    finalAnswer,
    processedNodes: order,
    currentProcessing: null,
    dpTakeRoot: dpTake[root],
    dpSkipRoot: dpSkip[root]
  });

  return { steps: stepResults, valueMap, adjacency: adj, parentMap, root, finalAnswer };
}

// ---------- Checkpoint Definitions ----------
const checkpointDefs = [
  {
    stepIndex: 3,
    nodeId: '2',
    question: 'Node 2 (value=2) has children 4 (value=10) and 5 (value=1). Their dp values are: dp_take(4)=10, dp_skip(4)=0; dp_take(5)=1, dp_skip(5)=0. Predict dp_take(2) and dp_skip(2).',
    inputFields: [
      { label: 'dp_take(2)', key: 'take2', type: 'number' },
      { label: 'dp_skip(2)', key: 'skip2', type: 'number' }
    ],
    checkAnswer: (answers) => {
      const take = parseInt(answers.take2, 10);
      const skip = parseInt(answers.skip2, 10);
      return take === 2 && skip === 11;
    },
    correctValues: { take2: 2, skip2: 11 },
    hint: 'Hint: dp_take[u] = value[u] + sum(dp_skip of children). Here children are 4 and 5 with skip=0 each, so dp_take(2) = 2 + 0 + 0 = 2. dp_skip[u] = sum(max(take[child], skip[child])). For child 4, max(10,0)=10; for child 5, max(1,0)=1; sum = 11.',
    explanation: 'Correct! dp_take(2) = 2 + 0 + 0 = 2; dp_skip(2) = max(10,0) + max(1,0) = 11.'
  },
  {
    stepIndex: 6,
    nodeId: 'root',
    question: 'Now change the value of node 4 from 10 to 15. Predict the new maximum development value.',
    inputFields: [
      { label: 'New maximum value', key: 'newMax', type: 'number' }
    ],
    checkAnswer: (answers) => {
      return parseInt(answers.newMax, 10) === 19;
    },
    correctValues: { newMax: 19 },
    hint: 'Hint: Recalculate bottom-up: Node 4 becomes 15. Node 2 dp_skip becomes max(15,0)+max(1,0)=16, dp_take remains 2. Node 1 dp_take = 3 + dp_skip(2) + dp_skip(3) = 3 + 16 + 0 = 19. dp_skip(1) = max(2,16)+max(1,0)=17. Max = 19.',
    explanation: 'Correct! With node 4 = 15, the new maximum is 19 (take root 1 with value 3 + skip children 2 and 3 = 3+16+0=19).'
  }
];

// ---------- Tree Structure for Visualization ----------
function buildTreeStructure(nodes, edges, root) {
  const valueMap = {};
  nodes.forEach(n => { valueMap[n.id] = n.value; });
  const adj = {};
  nodes.forEach(n => { adj[n.id] = []; });
  edges.forEach(([u, v]) => {
    adj[u].push(v);
    adj[v].push(u);
  });
  const visited = new Set();
  function build(id, parent) {
    visited.add(id);
    const children = (adj[id] || []).filter(neighbor => neighbor !== parent && !visited.has(neighbor));
    return {
      id,
      value: valueMap[id],
      children: children.map(child => build(child, id))
    };
  }
  return build(root, null);
}

// ---------- App Component ----------
function App() {
  const algorithmData = useMemo(() => computeAlgorithmSteps(INPUT_DATA), []);
  const { steps } = algorithmData;
  const treeStructure = useMemo(() => buildTreeStructure(INPUT_DATA.tree.nodes, INPUT_DATA.tree.edges, algorithmData.root), [algorithmData.root]);

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [logEntries, setLogEntries] = useState([]);
  const [checkpointState, setCheckpointState] = useState({});
  const logIdCounter = useRef(0);
  const mountedRef = useRef(false);

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogEntries(prev => [...prev, { id: ++logIdCounter.current, time, message, type }]);
  }, []);

  // Log initial only once (StrictMode safe)
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      addLog('Application started. Tree input loaded.', 'info');
    }
  }, [addLog]);

  const currentStep = steps[currentStepIndex];
  const totalSteps = steps.length;

  const goToStep = useCallback((idx) => {
    if (idx >= 0 && idx < totalSteps) {
      setCurrentStepIndex(idx);
      if (steps[idx].type === 'compute') {
        addLog(`Step ${idx}: Processing node ${steps[idx].nodeId} (dp_take=${steps[idx].dpTake}, dp_skip=${steps[idx].dpSkip})`, 'info');
      } else if (steps[idx].type === 'final') {
        addLog(`Algorithm finished. Final answer: ${steps[idx].finalAnswer}.`, 'info');
      }
    }
  }, [totalSteps, steps, addLog]);

  const handleNext = () => goToStep(currentStepIndex + 1);
  const handlePrev = () => goToStep(currentStepIndex - 1);

  // Auto-play
  const [autoPlay, setAutoPlay] = useState(false);
  const autoPlayRef = useRef(null);
  useEffect(() => {
    if (autoPlay) {
      autoPlayRef.current = setInterval(() => {
        setCurrentStepIndex(prev => {
          if (prev >= totalSteps - 1) {
            setAutoPlay(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
    } else {
      clearInterval(autoPlayRef.current);
    }
    return () => clearInterval(autoPlayRef.current);
  }, [autoPlay, totalSteps]);

  const toggleAutoPlay = () => {
    setAutoPlay(prev => !prev);
    addLog(autoPlay ? 'Auto-play stopped.' : 'Auto-play started.', 'info');
  };

  const handleReset = () => {
    setCurrentStepIndex(0);
    setCheckpointState({});
    setLogEntries([]);
    setAutoPlay(false);
    addLog('Reset to beginning.', 'info');
  };

  // Checkpoint handling
  const activeCheckpoint = checkpointDefs.find(cp => cp.stepIndex === currentStepIndex);
  const cpState = checkpointState[currentStepIndex] || { answers: {}, submitted: false, correct: null, showAnswer: false, showHint: false };

  const handleCpAnswerChange = (key, value) => {
    setCheckpointState(prev => ({
      ...prev,
      [currentStepIndex]: {
        ...(prev[currentStepIndex] || { answers: {}, submitted: false, correct: null, showAnswer: false, showHint: false }),
        answers: { ...(prev[currentStepIndex]?.answers || {}), [key]: value }
      }
    }));
  };

  const handleCpSubmit = () => {
    if (!activeCheckpoint) return;
    const isCorrect = activeCheckpoint.checkAnswer(cpState.answers);
    setCheckpointState(prev => ({
      ...prev,
      [currentStepIndex]: {
        ...(prev[currentStepIndex] || {}),
        submitted: true,
        correct: isCorrect,
        showAnswer: false,
        showHint: false
      }
    }));
    addLog(
      `Checkpoint at step ${currentStepIndex}: ${isCorrect ? 'Correct!' : 'Incorrect.'} (answer submitted)`,
      isCorrect ? 'correct' : 'incorrect'
    );
  };

  const handleCpShowHint = () => {
    setCheckpointState(prev => ({
      ...prev,
      [currentStepIndex]: {
        ...(prev[currentStepIndex] || {}),
        showHint: true
      }
    }));
    addLog(`Hint viewed for checkpoint at step ${currentStepIndex}.`, 'hint');
  };

  const handleCpShowAnswer = () => {
    setCheckpointState(prev => ({
      ...prev,
      [currentStepIndex]: {
        ...(prev[currentStepIndex] || {}),
        showAnswer: true
      }
    }));
    addLog(`Answer revealed for checkpoint at step ${currentStepIndex}.`, 'hint');
  };

  const treeCaption = () => {
    if (currentStep?.type === 'start') {
      return 'The tree is ready. Press Next to begin bottom-up DP computation.';
    }
    if (currentStep?.type === 'compute') {
      return `Processing node ${currentStep.nodeId} (value=${currentStep.nodeValue}).`;
    }
    if (currentStep?.type === 'final') {
      return 'All nodes processed. Final answer computed.';
    }
    return '';
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1>Tree DP: Maximum Independent Set</h1>
          <p className="header-subtitle">
            In a tree-shaped street network, adjacent plots cannot be developed simultaneously.
            Compute the maximum total development value using dynamic programming on trees.
          </p>
        </div>
        <span className="algorithm-tag">Tree DP</span>
      </header>

      <div className="main-content">
        <div className="tree-panel">
          <div className="card">
            <h2>Tree Visualization</h2>
            <TreeVisualization
              tree={treeStructure}
              highlightNode={currentStep?.currentProcessing || null}
              processedNodes={currentStep?.processedSoFar || currentStep?.processedNodes || []}
            />
            <div className="tree-caption">{treeCaption()}</div>
          </div>
          <div className="card">
            <h2>Input Data</h2>
            <JsonDisplay data={INPUT_DATA} />
            <div className="final-answer-section">
              <div className="final-answer-label">Expected Final Answer:</div>
              <div className="final-answer-value">{EXPECTED_FINAL_ANSWER}</div>
            </div>
            {currentStep?.type === 'final' && (
              <div className="final-answer-banner">
                Computed: max(dp_take[1], dp_skip[1]) = max({currentStep.dpTakeRoot}, {currentStep.dpSkipRoot}) = <strong>{currentStep.finalAnswer}</strong>
              </div>
            )}
          </div>
        </div>

        <div className="dp-panel">
          <div className="card">
            <h2>DP State Table</h2>
            {currentStep?.type === 'start' && (
              <div className="welcome-message">
                <span className="icon">🌳</span>
                This table will populate as nodes are processed bottom-up.
                <br />
                Press <strong>Next</strong> to start the postorder traversal.
              </div>
            )}
            <DpTable
              steps={steps}
              currentStepIndex={currentStepIndex}
            />
            {currentStep?.type === 'compute' && (
              <div className="dp-calculation">
                <p><span className="formula">{currentStep.formulaTake}</span></p>
                <p><span className="formula">{currentStep.formulaSkip}</span></p>
              </div>
            )}
            <StepControls
              currentStep={currentStepIndex}
              totalSteps={totalSteps}
              onPrev={handlePrev}
              onNext={handleNext}
              onReset={handleReset}
              autoPlay={autoPlay}
              onToggleAutoPlay={toggleAutoPlay}
            />
          </div>

          {activeCheckpoint && (
            <CheckpointPanel
              checkpoint={activeCheckpoint}
              state={cpState}
              onAnswerChange={handleCpAnswerChange}
              onSubmit={handleCpSubmit}
              onShowHint={handleCpShowHint}
              onShowAnswer={handleCpShowAnswer}
            />
          )}

          {!activeCheckpoint && currentStep?.type !== 'start' && currentStep?.type !== 'final' && (
            <div className="card" style={{ textAlign: 'center', color: '#64748b', fontSize: '0.85rem', padding: '14px' }}>
              Continue stepping through. Checkpoints await at node 2 and after the final answer.
            </div>
          )}
        </div>
      </div>

      <LearningLog entries={logEntries} />
    </div>
  );
}

export default App;