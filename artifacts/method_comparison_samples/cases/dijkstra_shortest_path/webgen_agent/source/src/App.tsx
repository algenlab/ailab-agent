import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import GraphView from './components/GraphView';
import StatePanel from './components/StatePanel';
import StepControls from './components/StepControls';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import { AlgorithmStep, ActivityEntry } from './types';
import { runDijkstra, formatDistance } from './dijkstra';
import { problemInput, expectedAnswer } from './data';

let activityIdCounter = 0;

function createActivityEntry(
  action: string,
  detail: string,
  type: ActivityEntry['type']
): ActivityEntry {
  activityIdCounter++;
  const now = new Date();
  const ts = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
  return {
    id: activityIdCounter,
    timestamp: ts,
    action,
    detail,
    type,
  };
}

export default function App() {
  const { steps, finalAnswer } = useMemo(() => runDijkstra(problemInput), []);
  const [stepIndex, setStepIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>(() => [
    createActivityEntry('📚 页面加载', 'Dijkstra 最短路算法交互式学习已就绪', 'system'),
  ]);
  const autoPlayRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentStep: AlgorithmStep = steps[stepIndex] || steps[steps.length - 1];

  const addActivity = useCallback(
    (entry: Omit<ActivityEntry, 'id' | 'timestamp'>) => {
      setActivityLog((prev) => [
        ...prev,
        createActivityEntry(entry.action, entry.detail, entry.type),
      ]);
    },
    []
  );

  // Cleanup autoplay on unmount
  useEffect(() => {
    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, []);

  const handlePrev = useCallback(() => {
    setStepIndex((prev) => {
      const next = Math.max(0, prev - 1);
      addActivity({
        action: '◀ 上一步',
        detail: `从步骤 ${prev + 1} 回到步骤 ${next + 1}`,
        type: 'navigation',
      });
      return next;
    });
    setIsAutoPlaying(false);
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
  }, [addActivity]);

  const handleNext = useCallback(() => {
    setStepIndex((prev) => {
      const next = Math.min(steps.length - 1, prev + 1);
      addActivity({
        action: '▶ 下一步',
        detail: `从步骤 ${prev + 1} 前进到步骤 ${next + 1}`,
        type: 'navigation',
      });
      if (next >= steps.length - 1) {
        setIsAutoPlaying(false);
        if (autoPlayRef.current) {
          clearInterval(autoPlayRef.current);
          autoPlayRef.current = null;
        }
      }
      return next;
    });
  }, [steps.length, addActivity]);

  const handleReset = useCallback(() => {
    setStepIndex(0);
    setIsAutoPlaying(false);
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
    addActivity({
      action: '⏮ 重置',
      detail: '算法步骤已重置到初始状态',
      type: 'navigation',
    });
  }, [addActivity]);

  const handleAutoPlay = useCallback(() => {
    if (isAutoPlaying) {
      setIsAutoPlaying(false);
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current);
        autoPlayRef.current = null;
      }
      addActivity({
        action: '⏸ 暂停',
        detail: '自动播放已暂停',
        type: 'navigation',
      });
    } else {
      if (stepIndex >= steps.length - 1) {
        handleReset();
      }
      setIsAutoPlaying(true);
      addActivity({
        action: '▶ 自动播放',
        detail: '开始自动播放算法步骤',
        type: 'navigation',
      });
      const interval = setInterval(() => {
        setStepIndex((prev) => {
          const next = prev + 1;
          if (next >= steps.length - 1) {
            setIsAutoPlaying(false);
            if (autoPlayRef.current) {
              clearInterval(autoPlayRef.current);
              autoPlayRef.current = null;
            }
            return steps.length - 1;
          }
          return next;
        });
      }, 1800);
      autoPlayRef.current = interval;
    }
  }, [isAutoPlaying, stepIndex, steps.length, handleReset, addActivity]);

  const handleEdgeHover = useCallback((key: string | null) => {
    setHoveredEdge(key);
  }, []);

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🛣 Dijkstra 最短路算法</h1>
        <p className="subtitle">算法家族：最短路 / MST · 交互式学习</p>
      </header>

      {/* Main content */}
      <div className="main-container">
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Problem description */}
          <div className="card problem-info">
            <div className="card-header">📋 问题描述</div>
            <div className="card-body">
              <p style={{ fontSize: '0.9rem', marginBottom: '10px', lineHeight: 1.7 }}>
                城市应急调度中心维护一张<strong>非负耗时的有向道路网</strong>，每个节点表示路口，每条边权表示从一个路口到另一个路口的通行时间。给定救援车辆出发路口{' '}
                <strong>start</strong>，返回它到所有可达路口的<strong>最短路通行时间</strong>。
              </p>
              <div className="input-block">
                <div className="label">📥 输入 (JSON)</div>
                <pre>{JSON.stringify(problemInput, null, 2)}</pre>
              </div>
              <div className="answer-block">
                <div className="label" style={{ color: 'var(--success)' }}>
                  ✅ 期望输出 (JSON)
                </div>
                <pre>{JSON.stringify(expectedAnswer)}</pre>
              </div>
            </div>
          </div>

          {/* Graph visualization */}
          <div className="card">
            <div className="card-header">
              🎨 图可视化
              <div className="legend" style={{ marginLeft: 'auto' }}>
                <span className="legend-item">
                  <span className="legend-dot ld-default" /> 未访问
                </span>
                <span className="legend-item">
                  <span className="legend-dot ld-visited" /> 已访问
                </span>
                <span className="legend-item">
                  <span className="legend-dot ld-current" /> 当前节点
                </span>
                <span className="legend-item">
                  <span className="legend-edge le-updated" /> 边松弛(更新)
                </span>
              </div>
            </div>
            <div className="card-body no-padding">
              <GraphView
                step={currentStep}
                stepIndex={stepIndex}
                relaxedEdges={currentStep.relaxedEdges}
                hoveredEdge={hoveredEdge}
                onEdgeHover={handleEdgeHover}
              />
            </div>
          </div>

          {/* Algorithm state */}
          <div className="card">
            <div className="card-header">📊 算法状态</div>
            <div className="card-body">
              <StatePanel step={currentStep} />
            </div>
          </div>

          {/* Step description */}
          <div className="card">
            <div className="card-header">📝 步骤说明</div>
            <div className="card-body">
              <div className="step-description">{currentStep.description}</div>
            </div>
          </div>

          {/* Controls */}
          <div className="card">
            <div className="card-header">🎮 步骤控制</div>
            <div className="card-body">
              <StepControls
                stepIndex={stepIndex}
                totalSteps={steps.length}
                onPrev={handlePrev}
                onNext={handleNext}
                onReset={handleReset}
                onAutoPlay={handleAutoPlay}
                isAutoPlaying={isAutoPlaying}
              />
            </div>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Quiz */}
          <div className="card">
            <div className="card-header">🧠 学习检测</div>
            <div className="card-body">
              <QuizPanel onActivity={addActivity} />
            </div>
          </div>

          {/* Activity log */}
          <div className="card">
            <div className="card-header">📜 学习活动记录</div>
            <div className="card-body">
              <ActivityLog entries={activityLog} />
            </div>
          </div>

          {/* Learning objectives */}
          <div className="card">
            <div className="card-header">🎯 学习目标</div>
            <div className="card-body">
              <ul>
                <li>追踪堆中节点和距离的变化，理解松弛操作如何逐步逼近最短路径</li>
                <li>根据当前加权图状态预测下一个将被弹出的节点</li>
                <li>验证算法执行过程中的距离单调性与堆的不变性</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
