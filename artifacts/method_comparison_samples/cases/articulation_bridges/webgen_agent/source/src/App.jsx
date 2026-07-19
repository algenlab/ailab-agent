import React, { useState, useCallback, useMemo } from 'react';
import GraphVisualizer from './components/GraphVisualizer';
import AlgorithmSteps from './components/AlgorithmSteps';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import InputOutput from './components/InputOutput';
import { runTarjan, PROBLEM_INPUT, EXPECTED_OUTPUT, QUIZ_QUESTIONS } from './utils/algorithm';
import './App.css';

export default function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [activityEntries, setActivityEntries] = useState([]);
  const [activeTab, setActiveTab] = useState('algorithm');

  const algorithmResult = useMemo(() => runTarjan(PROBLEM_INPUT.graph), []);
  const { steps } = algorithmResult;

  const step = steps[currentStep] || null;

  const currentArticulation = useMemo(() => {
    const artic = new Set();
    for (let i = 0; i <= currentStep; i++) {
      const s = steps[i];
      if (s.type === 'articulation-found' || s.type === 'root-articulation') {
        artic.add(s.node);
      }
    }
    return [...artic].sort();
  }, [currentStep, steps]);

  const currentBridges = useMemo(() => {
    const bridges = [];
    for (let i = 0; i <= currentStep; i++) {
      const s = steps[i];
      if (s.type === 'bridge-found' && s.edge) {
        bridges.push([...s.edge].sort());
      }
    }
    return bridges.sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
  }, [currentStep, steps]);

  const isComplete = step && step.type === 'complete';

  function addLogEntry(entry) {
    setActivityEntries(prev => [...prev, { ...entry, id: Date.now() }]);
  }

  function handleStepChange(newStep) {
    setCurrentStep(newStep);
    const s = steps[newStep];
    if (s) {
      const typeMap = {
        'articulation-found': 'answer-correct',
        'bridge-found': 'answer-correct',
        'enter': 'step',
        'explore': 'step',
        'backtrack': 'step',
        'back-edge': 'step',
        'exit': 'step',
        'start-component': 'step',
        'complete': 'step',
        'root-articulation': 'answer-correct'
      };
      addLogEntry({
        type: typeMap[s.type] || 'step',
        message: s.description,
        timestamp: new Date().toLocaleTimeString()
      });
    }
  }

  function handleQuizAnswer(data) {
    if (data.action === 'hint') {
      addLogEntry({
        type: 'hint',
        message: `Q${data.questionId}: 请求提示`,
        timestamp: data.timestamp
      });
    } else if (data.action === 'show-answer') {
      addLogEntry({
        type: 'show-answer',
        message: `Q${data.questionId}: 查看答案 → ${data.correctAnswer}`,
        timestamp: data.timestamp
      });
    } else {
      addLogEntry({
        type: data.correct ? 'answer-correct' : 'answer-incorrect',
        message: `Q${data.questionId}: ${data.correct ? '✓ 正确' : '✗ 错误'} — ${data.selectedAnswer}`,
        timestamp: data.timestamp
      });
    }
  }

  const vizState = useMemo(() => {
    if (!step) return {};
    return {
      currentNode: step.node || step.from || null,
      visitedNodes: step.visited || new Set(),
      bridges: currentBridges,
      articulationPoints: currentArticulation,
      activeEdge: step.type === 'backtrack' ? { from: step.from, to: step.to } : null,
      exploringEdge: step.type === 'explore' ? { from: step.from, to: step.to } : null,
      dfn: step.dfn || {},
      low: step.low || {},
      highlightNodes: step.type === 'articulation-found' ? [step.node] :
                      step.type === 'bridge-found' && step.edge ? step.edge :
                      step.type === 'root-articulation' ? [step.node] : []
    };
  }, [step, currentBridges, currentArticulation]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🔗 割点和桥 <span className="tag">图高级算法</span></h1>
        <p className="subtitle">
          城市通信网络中，每个交换站对应一个节点，光纤连接对应无向边。
          找出所有<b>割点</b>（关键交换站）和<b>桥</b>（唯一光纤）。
        </p>
      </header>

      <div className="main-layout">
        <aside className="left-panel">
          <div className="tab-bar">
            <button
              className={`tab-btn ${activeTab === 'algorithm' ? 'active' : ''}`}
              onClick={() => setActiveTab('algorithm')}
            >
              🔍 算法追踪
            </button>
            <button
              className={`tab-btn ${activeTab === 'quiz' ? 'active' : ''}`}
              onClick={() => setActiveTab('quiz')}
            >
              📝 学习检测
            </button>
            <button
              className={`tab-btn ${activeTab === 'io' ? 'active' : ''}`}
              onClick={() => setActiveTab('io')}
            >
              📊 输入/输出
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'algorithm' && (
              <AlgorithmSteps
                steps={steps}
                currentStep={currentStep}
                onStepChange={handleStepChange}
                graph={PROBLEM_INPUT.graph}
              />
            )}
            {activeTab === 'quiz' && (
              <QuizPanel
                questions={QUIZ_QUESTIONS}
                onAnswer={handleQuizAnswer}
                activityLog={activityEntries}
              />
            )}
            {activeTab === 'io' && (
              <InputOutput
                input={PROBLEM_INPUT}
                expectedOutput={EXPECTED_OUTPUT}
                currentArticulation={currentArticulation}
                currentBridges={currentBridges}
                isComplete={isComplete}
              />
            )}
          </div>
        </aside>

        <main className="right-panel">
          <div className="viz-card">
            <GraphVisualizer
              graph={PROBLEM_INPUT.graph}
              {...vizState}
            />
          </div>

          <div className="bottom-cards">
            <div className="result-card">
              <h3>📊 当前结果</h3>
              <div className="result-row">
                <div className="result-item">
                  <span className="result-label">割点</span>
                  <span className="result-val">
                    [{currentArticulation.length > 0 ? currentArticulation.join(', ') : ''}]
                  </span>
                </div>
                <div className="result-item">
                  <span className="result-label">桥</span>
                  <span className="result-val">
                    [{currentBridges.map(([u, v]) => `(${u},${v})`).join(', ')}]
                  </span>
                </div>
              </div>
              {isComplete && (
                <div className="completion-badge">
                  ✅ 算法执行完成
                </div>
              )}
            </div>

            <ActivityLog entries={activityEntries} />
          </div>
        </main>
      </div>

      <footer className="app-footer">
        <p>Tarjan 算法 · DFS 维护 dfn/low/parent · low[child] > dfn[u] 判定桥 · low[child] >= dfn[u] 判定割点</p>
      </footer>
    </div>
  );
}