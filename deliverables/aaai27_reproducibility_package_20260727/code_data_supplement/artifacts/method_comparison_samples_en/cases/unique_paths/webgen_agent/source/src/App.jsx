import React, { useState, useCallback, useRef, useMemo } from 'react';
import { generateSteps, PROBLEM_INPUT, EXPECTED_ANSWER } from './data/steps';
import checkpointDefs from './data/checkpoints';
import DPTable from './components/DPTable';
import CheckpointPanel from './components/CheckpointPanel';
import LearningLog from './components/LearningLog';

const { steps, m, n } = generateSteps();
const TOTAL_STEPS = steps.length;

function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { hour12: false });
}

export default function App() {
  const [stepIndex, setStepIndex] = useState(0);
  const [logEntries, setLogEntries] = useState([]);
  const logIdRef = useRef(0);

  const addLog = useCallback((message) => {
    const id = ++logIdRef.current;
    setLogEntries((prev) => [
      ...prev,
      { id, time: formatTime(), message },
    ]);
  }, []);

  const currentStep = steps[stepIndex];
  const [ci, cj] = currentStep.cell;

  const goToStep = useCallback(
    (idx) => {
      const clamped = Math.max(0, Math.min(TOTAL_STEPS - 1, idx));
      setStepIndex(clamped);
      const s = steps[clamped];
      addLog(
        `Navigated to step ${clamped + 1}/${TOTAL_STEPS}: Computing dp[${s.cell[0]}][${s.cell[1]}] = ${s.value}.`
      );
    },
    [addLog, steps]
  );

  const handlePrev = () => goToStep(stepIndex - 1);
  const handleNext = () => goToStep(stepIndex + 1);
  const handleFirst = () => goToStep(0);
  const handleLast = () => goToStep(TOTAL_STEPS - 1);

  // Auto-play state
  const [autoPlaying, setAutoPlaying] = useState(false);
  const autoPlayRef = useRef(null);

  const startAutoPlay = useCallback(() => {
    setAutoPlaying(true);
    let idx = stepIndex;
    autoPlayRef.current = setInterval(() => {
      idx++;
      if (idx >= TOTAL_STEPS) {
        clearInterval(autoPlayRef.current);
        autoPlayRef.current = null;
        setAutoPlaying(false);
        setStepIndex(TOTAL_STEPS - 1);
        addLog('Auto-play completed — reached the final answer.');
        return;
      }
      setStepIndex(idx);
    }, 600);
    addLog('Auto-play started.');
  }, [stepIndex, addLog]);

  const stopAutoPlay = useCallback(() => {
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
    setAutoPlaying(false);
    addLog('Auto-play stopped.');
  }, [addLog]);

  // Determine which dp snapshot to show
  const dpSnapshot = currentStep.dpSnapshot;

  const progressPct = ((stepIndex + 1) / TOTAL_STEPS) * 100;

  // Verify that the final answer matches
  const finalCell = steps[TOTAL_STEPS - 1];
  const computedAnswer = finalCell.value;
  const answerMatches = computedAnswer === EXPECTED_ANSWER;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Unique Paths</h1>
        <span className="algo-family">Algorithm Family: 2D Dynamic Programming</span>
      </header>

      <main className="app-main">
        {/* Left column: problem + visualization */}
        <section className="main-left">
          {/* Problem display */}
          <div className="card problem-card">
            <h2>Problem Statement</h2>
            <p>
              In a smart warehouse with <strong>{PROBLEM_INPUT.m} rows</strong> and{' '}
              <strong>{PROBLEM_INPUT.n} columns</strong>, an inspection robot starts from the
              top-left charging point <code>(0,0)</code>. Each move can only be one step{' '}
              <strong>right</strong> or <strong>down</strong>. Compute the total number of distinct
              paths for the robot to reach the bottom-right packaging station{' '}
              <code>({PROBLEM_INPUT.m - 1},{PROBLEM_INPUT.n - 1})</code>.
            </p>
            <div className="problem-io">
              <div className="io-box">
                <span className="io-label">Input (JSON):</span>
                <code>{JSON.stringify(PROBLEM_INPUT)}</code>
              </div>
              <div className="io-box">
                <span className="io-label">Expected Answer:</span>
                <code className="answer-code">{EXPECTED_ANSWER}</code>
                {stepIndex === TOTAL_STEPS - 1 && (
                  <span
                    className={`answer-badge ${answerMatches ? 'answer-badge--match' : 'answer-badge--mismatch'}`}
                  >
                    {answerMatches ? 'Computed: ' + computedAnswer + ' ✓' : 'Mismatch!'}
                  </span>
                )}
              </div>
            </div>
            <p className="combinatorics-note">
              <em>Verification with combinatorics:</em>{' '}
              C(m+n−2, n−1) = C({PROBLEM_INPUT.m}+{PROBLEM_INPUT.n}−2, {PROBLEM_INPUT.n}−1) = C(8, 6) = 28.
            </p>
          </div>

          {/* DP Table Visualization */}
          <div className="card viz-card">
            <h2>DP Table Visualization</h2>
            <DPTable
              dpSnapshot={dpSnapshot}
              m={m}
              n={n}
              currentCell={currentStep.cell}
              aboveVal={currentStep.above}
              leftVal={currentStep.left}
              currentValue={currentStep.value}
            />

            {/* Step Controls */}
            <div className="step-controls">
              <div className="step-nav">
                <button
                  onClick={handleFirst}
                  disabled={stepIndex === 0 || autoPlaying}
                  className="btn btn-nav"
                  aria-label="Go to first step"
                  title="First step"
                >
                  ⏮
                </button>
                <button
                  onClick={handlePrev}
                  disabled={stepIndex === 0 || autoPlaying}
                  className="btn btn-nav"
                  aria-label="Previous step"
                  title="Previous step"
                >
                  ◀
                </button>
                <span className="step-indicator">
                  Step <strong>{stepIndex + 1}</strong> of {TOTAL_STEPS}
                </span>
                <button
                  onClick={handleNext}
                  disabled={stepIndex === TOTAL_STEPS - 1 || autoPlaying}
                  className="btn btn-nav"
                  aria-label="Next step"
                  title="Next step"
                >
                  ▶
                </button>
                <button
                  onClick={handleLast}
                  disabled={stepIndex === TOTAL_STEPS - 1 || autoPlaying}
                  className="btn btn-nav"
                  aria-label="Go to last step"
                  title="Last step"
                >
                  ⏭
                </button>
              </div>

              <div className="step-progress">
                <div className="progress-bar" style={{ width: `${progressPct}%` }} />
              </div>

              <div className="step-auto">
                {!autoPlaying ? (
                  <button onClick={startAutoPlay} className="btn btn-auto" disabled={stepIndex === TOTAL_STEPS - 1}>
                    ▶ Auto-play
                  </button>
                ) : (
                  <button onClick={stopAutoPlay} className="btn btn-auto btn-auto--stop">
                    ⏹ Stop
                  </button>
                )}
              </div>

              <div className="step-slider">
                <input
                  type="range"
                  min={0}
                  max={TOTAL_STEPS - 1}
                  value={stepIndex}
                  onChange={(e) => goToStep(parseInt(e.target.value, 10))}
                  disabled={autoPlaying}
                  aria-label="Step slider"
                  className="slider"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Right column: checkpoints + log */}
        <aside className="main-right">
          <CheckpointPanel checkpoints={checkpointDefs} onLog={addLog} />
          <LearningLog entries={logEntries} />
        </aside>
      </main>
    </div>
  );
}
