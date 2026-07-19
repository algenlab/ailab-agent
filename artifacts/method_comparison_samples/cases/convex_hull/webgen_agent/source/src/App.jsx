import { useState, useMemo, useCallback, useRef } from 'react';
import { generateTrace, getCheckpointInfo } from './algorithm';
import Canvas from './Canvas';
import TracePanel from './TracePanel';
import Checkpoint from './Checkpoint';
import LearningLog from './LearningLog';

const INPUT_POINTS = [[0,0],[1,1],[2,0],[1,2]];
const EXPECTED_OUTPUT = [[0,0],[2,0],[1,2]];
const INPUT_JSON_STRING = JSON.stringify(INPUT_POINTS);
const OUTPUT_JSON_STRING = JSON.stringify(EXPECTED_OUTPUT);

const LEARNING_OBJECTIVES = [
  "理解 Andrew 单调链如何通过上下凸壳的交替构建实现凸包检测。",
  "能够根据 trace 中 current 点的位置和 lower/upper 状态预测下一步操作。",
  "辨别凸包构建过程中的不变式，如转向判别 cross <= 0 表示需要回退。"
];

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef(null);

  const handleCopy = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      timerRef.current = setTimeout(() => setCopied(false), 1500);
    }).catch(() => {
      // Fallback for environments without clipboard API
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); setCopied(true); timerRef.current = setTimeout(() => setCopied(false), 1500); } catch(e) {}
      document.body.removeChild(ta);
    });
  }, [text]);

  return (
    <button className={`copy-btn${copied ? ' copied' : ''}`} onClick={handleCopy}>
      {copied ? '✓ 已复制' : '📋 复制'}
    </button>
  );
}

export default function App() {
  const { trace, finalHull } = useMemo(() => generateTrace(INPUT_POINTS), []);
  const [currentStep, setCurrentStep] = useState(0);
  const [logEntries, setLogEntries] = useState([]);

  const checkpointInfo = useMemo(() => getCheckpointInfo(trace), [trace]);
  const checkpointStep = checkpointInfo?.stepIndex || 0;

  const logAction = useCallback((message) => {
    setLogEntries(prev => [...prev, { time: new Date(), message }]);
  }, []);

  const handleStepChange = useCallback((step) => {
    if (step !== currentStep) {
      logAction(`跳转至步骤 ${step}`);
    }
    setCurrentStep(step);
  }, [currentStep, logAction]);

  return (
    <div className="app">
      <header>
        <h1>凸包 <span className="category">几何 / 扫描线</span></h1>
      </header>

      <section className="problem">
        <h2>问题描述</h2>
        <p>在快递配送中，你拿到一个投递点列表 <code>points</code>，每个点用一个二维坐标 (x, y) 表示。你需要计算能包围所有投递点的最小凸多边形的顶点，并按照 <strong>Andrew 单调链算法</strong>的输出顺序返回这些顶点的坐标列表。返回的顶点应按照<strong>逆时针顺序</strong>排列，并且<strong>不包含共线的中间点</strong>。</p>
      </section>

      <div className="io-panels">
        <div className="input-panel">
          <h3>📥 输入 (points)</h3>
          <div className="code-block-wrapper">
            <pre>{INPUT_JSON_STRING}</pre>
            <CopyButton text={INPUT_JSON_STRING} />
          </div>
        </div>
        <div className="output-panel">
          <h3>📤 预期答案</h3>
          <div className="code-block-wrapper">
            <pre>{OUTPUT_JSON_STRING}</pre>
            <CopyButton text={OUTPUT_JSON_STRING} />
          </div>
        </div>
      </div>

      <div className="learning-objectives">
        <h3>🎯 学习目标</h3>
        <ul>
          {LEARNING_OBJECTIVES.map((obj, i) => <li key={i}>{obj}</li>)}
        </ul>
      </div>

      <div className="main-area">
        <div className="canvas-section">
          <Canvas points={INPUT_POINTS} trace={trace} currentStep={currentStep} width={420} height={400} margin={45} />
        </div>
        <div className="trace-section">
          <TracePanel trace={trace} currentStep={currentStep} onStepChange={handleStepChange} />
        </div>
      </div>

      <Checkpoint
        logAction={logAction}
        checkpointStep={checkpointStep}
        currentStep={currentStep}
        state={checkpointInfo}
      />

      <LearningLog entries={logEntries} />
    </div>
  );
}