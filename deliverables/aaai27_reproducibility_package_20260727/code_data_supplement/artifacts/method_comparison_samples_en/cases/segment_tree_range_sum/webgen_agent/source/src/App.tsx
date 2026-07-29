import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import ProblemDisplay from './components/ProblemDisplay';
import SegmentTreeView from './components/SegmentTreeView';
import Controls from './components/Controls';
import CheckpointPanel from './components/CheckpointPanel';
import ActivityLog from './components/ActivityLog';
import { SegmentTree } from './types';
import {
  buildSegmentTree,
  queryRange,
  updatePoint,
  getNodesAtLevel,
  cloneTree,
} from './segmentTreeUtils';
import {
  INITIAL_INPUT,
  INITIAL_CHECKPOINTS,
  SAMPLE_HINTS,
  SAMPLE_ANSWERS,
} from './data';

type Step = 'initial' | 'built' | 'query' | 'update' | 'complete';

function App() {
  const { nums, query, update } = INITIAL_INPUT;
  const [currentStep, setCurrentStep] = useState<Step>('initial');
  const [tree, setTree] = useState<SegmentTree | null>(null);
  const [beforeResult, setBeforeResult] = useState<number | null>(null);
  const [afterResult, setAfterResult] = useState<number | null>(null);
  const [highlightedPath, setHighlightedPath] = useState<number[]>([]);
  const [visitedNodes, setVisitedNodes] = useState<number[]>([]);
  const [logEntries, setLogEntries] = useState<string[]>([]);
  const [checkpointResponses, setCheckpointResponses] = useState<Record<number, string>>({});
  const [checkpointResults, setCheckpointResults] = useState<Record<number, boolean | null>>({});
  const [showHints, setShowHints] = useState<Record<number, boolean>>({});
  const [showAnswers, setShowAnswers] = useState<Record<number, boolean>>({});
  const [activeCheckpoint, setActiveCheckpoint] = useState<number>(1);

  const addLog = useCallback((message: string) => {
    setLogEntries((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] ${message}`,
    ]);
  }, []);

  const handleBuild = useCallback(() => {
    const newTree = buildSegmentTree(nums, 0, nums.length - 1);
    setTree(newTree);
    setBeforeResult(null);
    setAfterResult(null);
    setHighlightedPath([]);
    setVisitedNodes([]);
    setCurrentStep('built');
    addLog(`Segment tree built from nums = [${nums.join(', ')}]`);
  }, [nums, addLog]);

  const handleQuery = useCallback(() => {
    if (!tree) return;
    const [l, r] = query;
    const visited: number[] = [];
    const result = queryRange(tree, l, r, visited);
    setBeforeResult(result);
    setVisitedNodes(visited);
    setHighlightedPath(visited);
    setCurrentStep('query');
    addLog(
      `Range query [${l}, ${r}] completed. Visited nodes: [${visited.join(', ')}]. Sum = ${result}`
    );
  }, [tree, query, addLog]);

  const handleUpdate = useCallback(() => {
    if (!tree) return;
    const [pos, val] = update;
    const originalTree = cloneTree(tree);
    const updatePath: number[] = [];
    const newTree = updatePoint(originalTree, pos, val, updatePath);
    setTree(newTree);
    setHighlightedPath(updatePath);
    setCurrentStep('update');
    addLog(
      `Update: nums[${pos}] changed from ${nums[pos]} to ${val}. Update path (bottom-up): [${updatePath.join(', ')}]`
    );
  }, [tree, update, nums, addLog]);

  const handleReQuery = useCallback(() => {
    if (!tree) return;
    const [l, r] = query;
    const visited: number[] = [];
    const result = queryRange(tree, l, r, visited);
    setAfterResult(result);
    setVisitedNodes(visited);
    setHighlightedPath(visited);
    setCurrentStep('complete');
    addLog(
      `Re-query [${l}, ${r}] after update. Sum = ${result}. Final answer: {"before": ${beforeResult}, "after": ${result}}`
    );
  }, [tree, query, beforeResult, addLog]);

  const handleReset = useCallback(() => {
    setTree(null);
    setBeforeResult(null);
    setAfterResult(null);
    setHighlightedPath([]);
    setVisitedNodes([]);
    setCurrentStep('initial');
    setLogEntries([]);
    setCheckpointResponses({});
    setCheckpointResults({});
    setShowHints({});
    setShowAnswers({});
    setActiveCheckpoint(1);
    addLog('Session reset. Ready to start.');
  }, [addLog]);

  const handleCheckpointSubmit = useCallback(
    (id: number, answer: string) => {
      const checkpoint = INITIAL_CHECKPOINTS.find((c) => c.id === id);
      if (!checkpoint) return;
      const isCorrect =
        answer.trim().toLowerCase() === checkpoint.correctAnswer.trim().toLowerCase();
      setCheckpointResponses((prev) => ({ ...prev, [id]: answer }));
      setCheckpointResults((prev) => ({ ...prev, [id]: isCorrect }));
      if (isCorrect) {
        addLog(`Checkpoint ${id}: Correct! "${answer}" is right.`);
      } else {
        addLog(`Checkpoint ${id}: Incorrect. You answered "${answer}".`);
      }
    },
    [addLog]
  );

  const handleShowHint = useCallback((id: number) => {
    setShowHints((prev) => ({ ...prev, [id]: !prev[id] }));
    addLog(`Hint for question ${id} ${showHints[id] ? 'hidden' : 'revealed'}.`);
  }, [showHints, addLog]);

  const handleShowAnswer = useCallback(
    (id: number) => {
      setShowAnswers((prev) => ({ ...prev, [id]: true }));
      const checkpoint = INITIAL_CHECKPOINTS.find((c) => c.id === id);
      if (checkpoint) {
        addLog(`Answer for question ${id} revealed: ${checkpoint.correctAnswer}`);
      }
    },
    [addLog]
  );

  const nodesByLevel = tree ? getNodesAtLevel(tree) : [];

  return (
    <div className="container" style={{ paddingBottom: '32px' }}>
      <Header />
      <ProblemDisplay
        nums={nums}
        query={query}
        update={update}
        before={beforeResult}
        after={afterResult}
      />
      <Controls
        currentStep={currentStep}
        onBuild={handleBuild}
        onQuery={handleQuery}
        onUpdate={handleUpdate}
        onReQuery={handleReQuery}
        onReset={handleReset}
      />
      <SegmentTreeView
        nodesByLevel={nodesByLevel}
        highlightedPath={highlightedPath}
        visitedNodes={visitedNodes}
        nums={nums}
      />
      <div style={{ display: 'flex', gap: '24px', marginTop: '24px', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 380px', minWidth: 0 }}>
          <CheckpointPanel
            checkpoints={INITIAL_CHECKPOINTS}
            activeCheckpoint={activeCheckpoint}
            onSelectCheckpoint={setActiveCheckpoint}
            responses={checkpointResponses}
            results={checkpointResults}
            showHints={showHints}
            showAnswers={showAnswers}
            hints={SAMPLE_HINTS}
            answers={SAMPLE_ANSWERS}
            onSubmit={handleCheckpointSubmit}
            onShowHint={handleShowHint}
            onShowAnswer={handleShowAnswer}
            currentStep={currentStep}
          />
        </div>
        <div style={{ flex: '1 1 340px', minWidth: 0 }}>
          <ActivityLog entries={logEntries} />
        </div>
      </div>
    </div>
  );
}

export default App;
