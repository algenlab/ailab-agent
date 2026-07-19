
import React, { useState, useCallback, useMemo } from 'react';
import TreeVisualization from './components/TreeVisualization';
import DPStateTable from './components/DPStateTable';
import StepNavigation from './components/StepNavigation';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import {
  initialTree,
  buildTree,
  computeCorrectDP,
  generateInitialSteps,
  computeLayout,
} from './algorithm';

const initialData = generateInitialSteps(initialTree.nodes, initialTree.edges);
const { dp_take: finalTake, dp_skip: finalSkip } = computeCorrectDP(initialTree.nodes, initialTree.edges);
const finalAnswer = Math.max(finalTake["1"], finalSkip["1"]);

export default function App() {
  const [steps, setSteps] = useState(initialData.steps);
  const [stepIndex, setStepIndex] = useState(0);
  const [dpTake, setDpTake] = useState({});
  const [dpSkip, setDpSkip] = useState({});
  const [log, setLog] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [userFinalAnswer, setUserFinalAnswer] = useState('');
  const [finalAnswerFeedback, setFinalAnswerFeedback] = useState(null);

  const treeInfo = useMemo(() => buildTree(initialTree.nodes, initialTree.edges), []);
  const layout = useMemo(() => computeLayout(treeInfo.root, treeInfo.children), [treeInfo]);
  const nodeIds = useMemo(() => initialTree.nodes.map(n => n.id), []);

  const allComputed = useMemo(() => Object.keys(dpTake).length === nodeIds.length, [dpTake, nodeIds]);
  const computedAnswer = useMemo(() => {
    if (!allComputed) return null;
    return Math.max(dpTake["1"], dpSkip["1"]);
  }, [allComputed, dpTake, dpSkip]);

  const addLog = useCallback((message, type = '') => {
    setLog(prev => [...prev, { message, type }]);
  }, []);

  const handleCheckFinalAnswer = useCallback(() => {
    const val = parseInt(userFinalAnswer, 10);
    if (isNaN(val)) {
      setFinalAnswerFeedback({ status: 'incorrect', message: '请输入有效数字' });
      return;
    }
    if (val === finalAnswer) {
      setFinalAnswerFeedback({ status: 'correct', message: '正确！你的答案与预期结果一致！' });
      addLog(`最终答案测试：输入 ${val} — 正确`, 'correct');
    } else {
      setFinalAnswerFeedback({
        status: 'incorrect',
        message: `你的答案 ${val} 不正确，正确答案是 ${finalAnswer}`
      });
      addLog(`最终答案测试：输入 ${val} — 错误（正确答案 ${finalAnswer}）`, 'incorrect');
    }
  }, [userFinalAnswer, addLog]);

  const currentStep = steps[stepIndex];

  const canGoNext = useMemo(() => {
    if (!currentStep) return false;
    if (currentStep.type === 'start') return true;
    if (currentStep.type === 'process') {
      if (currentStep.requiresPrediction && !currentStep.solved) return false;
      if (currentStep.completed) return true;
      return currentStep.solved || !currentStep.requiresPrediction;
    }
    return true;
  }, [currentStep]);

  const stepDescription = useMemo(() => {
    if (!currentStep) return '';
    if (currentStep.type === 'start') return '开始：初始化，尚未计算任何节点。请点击"下一步"开始遍历';
    if (currentStep.type === 'process') {
      const node = currentStep.nodeId;
      if (currentStep.completed) {
        return `✓ 节点 ${node} 处理完毕：dp_take=${currentStep.correctTake}，dp_skip=${currentStep.correctSkip}`;
      }
      if (currentStep.requiresPrediction) {
        return `处理节点 ${node}（value=${currentStep.value}）：请根据子节点的 DP 值预测 dp_take 和 dp_skip`;
      }
      return `处理叶子节点 ${node}（value=${currentStep.value}）：无子节点，dp_take=${currentStep.value}，dp_skip=0`;
    }
    return '';
  }, [currentStep]);

  const handleNext = useCallback(() => {
    const step = steps[stepIndex];
    if (!step) return;
    if (step.type === 'start') {
      setStepIndex(prev => prev + 1);
      addLog('开始遍历树，按照后序遍历顺序处理节点');
      return;
    }
    if (step.type === 'process') {
      if (step.requiresPrediction && !step.solved) {
        alert('请先完成预测或使用"显示答案"后再继续');
        return;
      }
      if (!step.completed) {
        const updatedSteps = steps.map((s, i) =>
          i === stepIndex ? { ...s, completed: true, userTake: step.userTake, userSkip: step.userSkip } : s
        );
        setSteps(updatedSteps);
        const newTake = { ...dpTake };
        const newSkip = { ...dpSkip };
        newTake[step.nodeId] = step.correctTake;
        newSkip[step.nodeId] = step.correctSkip;
        setDpTake(newTake);
        setDpSkip(newSkip);
        addLog(`节点 ${step.nodeId} 计算完成: dp_take=${step.correctTake}, dp_skip=${step.correctSkip}`, 'compute');
      }
      setStepIndex(prev => prev + 1);
      setFeedback(null);
      setHintVisible(false);
    }
  }, [stepIndex, steps, dpTake, dpSkip, addLog]);

  const handlePrev = useCallback(() => {
    if (stepIndex > 0) {
      setStepIndex(prev => prev - 1);
      setFeedback(null);
      setHintVisible(false);
    }
  }, [stepIndex]);

  const handleReset = useCallback(() => {
    const newData = generateInitialSteps(initialTree.nodes, initialTree.edges);
    setSteps(newData.steps);
    setStepIndex(0);
    setDpTake({});
    setDpSkip({});
    setLog([]);
    setFeedback(null);
    setHintVisible(false);
    setUserFinalAnswer('');
    setFinalAnswerFeedback(null);
    addLog('已重置 — 所有 DP 状态和预测已清除');
  }, [addLog]);

  const handleCheck = useCallback((userTake, userSkip) => {
    const step = steps[stepIndex];
    if (!step || step.type !== 'process') return;
    const correctTake = step.correctTake;
    const correctSkip = step.correctSkip;
    if (userTake === correctTake && userSkip === correctSkip) {
      const updatedSteps = steps.map((s, i) =>
        i === stepIndex
          ? { ...s, solved: true, userTake, userSkip, showAnswerUsed: false }
          : s
      );
      setSteps(updatedSteps);
      setFeedback({ status: 'correct', message: '✓ 正确！可点击"下一步"继续' });
      addLog(`预测节点 ${step.nodeId}: dp_take=${userTake}, dp_skip=${userSkip} — ✓ 正确`, 'correct');
    } else {
      setFeedback({
        status: 'incorrect',
        message: `✗ 不正确。正确答案：dp_take=${correctTake}, dp_skip=${correctSkip}。请重试或使用提示`
      });
      addLog(`预测节点 ${step.nodeId}: dp_take=${userTake}, dp_skip=${userSkip} — ✗ 错误`, 'incorrect');
    }
  }, [stepIndex, steps, addLog]);

  const handleHint = useCallback(() => {
    const step = steps[stepIndex];
    setHintVisible(prev => !prev);
    if (!hintVisible) {
      addLog(`查看提示：节点 ${step.nodeId} — dp_take[u]=value[u]+Σdp_skip[child], dp_skip[u]=Σmax(dp_take[child],dp_skip[child])`, 'hint');
    }
  }, [stepIndex, steps, addLog, hintVisible]);

  const handleShowAnswer = useCallback(() => {
    const step = steps[stepIndex];
    if (!step || step.type !== 'process') return;
    const updatedSteps = steps.map((s, i) =>
      i === stepIndex
        ? { ...s, solved: true, showAnswerUsed: true, userTake: step.correctTake, userSkip: step.correctSkip }
        : s
    );
    setSteps(updatedSteps);
    setFeedback(null);
    setHintVisible(false);
    addLog(`显示答案 节点 ${step.nodeId}: dp_take=${step.correctTake}, dp_skip=${step.correctSkip}`, 'showAnswer');
  }, [stepIndex, steps, addLog]);

  const currentNode = currentStep?.type === 'process' ? currentStep.nodeId : null;

  return (
    <div className="app-container">
      <header>
        <h1>树形 DP 最大独立集</h1>
        <p className="subtitle">
          算法家族：<strong>树形 DP</strong>  | 
          问题：在树形街道中选择不邻接的地段，使总开发价值最大
        </p>
      </header>
      <div className="main-content">
        <div className="left-panel">
          <section className="problem-input">
            <h2>📋 问题输入</h2>
            <div className="input-dual">
              <div className="input-wrapper">
                <pre className="json-block">{
`{
  "tree": {
    "nodes": [
      { "id": "1", "value": 3 },
      { "id": "2", "value": 2 },
      { "id": "3", "value": 1 },
      { "id": "4", "value": 10 },
      { "id": "5", "value": 1 }
    ],
    "edges": [
      ["1", "2"],
      ["1", "3"],
      ["2", "4"],
      ["2", "5"]
    ]
  }
}`}</pre>
              </div>
              <div className="input-tree-preview">
                <h4>树形结构预览</h4>
                <TreeVisualization
                  layout={layout}
                  children={treeInfo.children}
                  values={treeInfo.values}
                  dpTake={dpTake}
                  dpSkip={dpSkip}
                  currentNode={currentNode}
                  nodeIds={nodeIds}
                  compact={true}
                />
              </div>
            </div>
          </section>
          <section className="visualization">
            <h2>🌳 DP 状态可视化</h2>
            <div className="vis-legend">
              <span className="legend-item"><span className="legend-dot current"></span> 当前节点</span>
              <span className="legend-item"><span className="legend-dot computed"></span> 已计算</span>
              <span className="legend-item"><span className="legend-dot pending"></span> 待计算</span>
            </div>
            <TreeVisualization
              layout={layout}
              children={treeInfo.children}
              values={treeInfo.values}
              dpTake={dpTake}
              dpSkip={dpSkip}
              currentNode={currentNode}
              nodeIds={nodeIds}
              compact={false}
            />
            <DPStateTable
              nodeIds={nodeIds}
              values={treeInfo.values}
              dpTake={dpTake}
              dpSkip={dpSkip}
            />
          </section>
          <section className="step-area">
            <StepNavigation
              stepIndex={stepIndex}
              totalSteps={steps.length}
              onPrev={handlePrev}
              onNext={handleNext}
              onReset={handleReset}
              canGoNext={canGoNext}
              currentStepDesc={stepDescription}
            />
            {currentStep?.type === 'process' && currentStep.requiresPrediction && !currentStep.solved && (
              <QuizPanel
                step={currentStep}
                onCheck={handleCheck}
                onHint={handleHint}
                onShowAnswer={handleShowAnswer}
                feedback={feedback}
              />
            )}
            {hintVisible && currentStep?.type === 'process' && (
              <div className="hint-box">
                <h4>💡 提示</h4>
                <p><strong>叶子节点</strong>（无子节点）：dp_take[u] = value[u], dp_skip[u] = 0</p>
                <p><strong>内部节点</strong>（有子节点）：</p>
                <ul>
                  <li><code>dp_take[u] = value[u] + Σ dp_skip[child]</code>  (选 u，子节点都不能选)</li>
                  <li><code>dp_skip[u] = Σ max(dp_take[child], dp_skip[child])</code>  (不选 u，子节点可选可不选)</li>
                </ul>
                {currentStep.children.length > 0 && (
                  <div className="hint-detail">
                    <p>当前节点 {currentStep.nodeId} 的子节点 DP 值：</p>
                    <ul>
                      {currentStep.children.map(c =>
                        <li key={c.id}>节点 {c.id}: take={c.dp_take}, skip={c.dp_skip}</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
        <div className="right-panel">
          <section className="learning-objectives">
            <h3>🎯 学习目标</h3>
            <ul>
              <li>理解 <code>dp_take[u]</code>（选中 u 时的最优值）与 <code>dp_skip[u]</code>（不选 u 时的最优值）的定义与递推关系</li>
              <li>能够根据子节点的 dp 值预测父节点的状态更新</li>
              <li>通过修改节点权重观察全局最优解的变化，建立对状态依赖的直观感受</li>
            </ul>
          </section>
          <section className="final-answer">
            <h3>📊 最终答案</h3>
            <div className="answer-display">
              <span className="answer-label">算法计算值：</span>
              <span className="answer-value">
                {allComputed ? computedAnswer : '?'}
              </span>
            </div>
            <p className="answer-note">正确答案：<strong>{finalAnswer}</strong></p>
            <div className="answer-test">
              <h4>测试你的理解</h4>
              <p className="test-hint">不看上面的答案，你能算出最大总开发价值吗？</p>
              <div className="answer-input-row">
                <input
                  type="number"
                  placeholder="输入你的答案..."
                  value={userFinalAnswer}
                  onChange={e => setUserFinalAnswer(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCheckFinalAnswer()}
                />
                <button onClick={handleCheckFinalAnswer}>检查</button>
              </div>
              {finalAnswerFeedback && (
                <div className={`feedback ${finalAnswerFeedback.status}`}>
                  {finalAnswerFeedback.message}
                </div>
              )}
            </div>
          </section>
          <ActivityLog log={log} />
        </div>
      </div>
    </div>
  );
}
  