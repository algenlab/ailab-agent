import React, { useState, useCallback, useRef, useEffect } from 'react';

/* ===== Constants ===== */
const TEMPERATURES = [73, 74, 75, 71, 69, 72, 76, 73];
const FINAL_ANSWER = [1, 1, 4, 2, 1, 1, 0, 0];

/* ===== Trace Generator ===== */
function generateTrace(temps) {
  const n = temps.length;
  const stack = [];
  const answer = new Array(n).fill(0);
  const steps = [];

  for (let i = 0; i < n; i++) {
    // Check if we need to pop
    while (stack.length > 0 && temps[i] > temps[stack[stack.length - 1]]) {
      const popIdx = stack[stack.length - 1];
      steps.push({
        type: 'compare',
        currentIdx: i,
        currentTemp: temps[i],
        stackTopIdx: popIdx,
        stackTopTemp: temps[popIdx],
        action: 'popping',
        stackSnapshot: [...stack],
        answerSnapshot: [...answer],
        poppedIdx: popIdx,
        message: `Temperature ${temps[i]}°C > ${temps[popIdx]}°C at stack top (index ${popIdx}). Popping index ${popIdx} and writing answer[${popIdx}] = ${i} - ${popIdx} = ${i - popIdx}.`,
      });
      answer[popIdx] = i - popIdx;
      stack.pop();
    }

    // Push current
    steps.push({
      type: 'push',
      currentIdx: i,
      currentTemp: temps[i],
      stackSnapshot: [...stack, i],
      answerSnapshot: [...answer],
      message: stack.length === 0
        ? `Stack is empty. Pushing index ${i} (${temps[i]}°C) onto the stack.`
        : `Temperature ${temps[i]}°C <= stack top ${temps[stack[stack.length - 1]]}°C. Pushing index ${i} (${temps[i]}°C) onto the stack.`,
    });
    stack.push(i);
  }

  // Remaining zeros
  steps.push({
    type: 'complete',
    currentIdx: n,
    currentTemp: null,
    stackSnapshot: [...stack],
    answerSnapshot: [...answer],
    message: `Scan complete. Indices remaining in stack (${stack.length > 0 ? stack.join(', ') : 'none'}) have no future warmer day. Their answer values remain 0.`,
  });

  return steps;
}

/* ===== Utility ===== */
function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/* ===== Components ===== */

function ArrayDisplay({ label, values, highlightIdx, highlightType, dayPrefix }) {
  if (!values || values.length === 0) return null;
  return (
    <div className="problem-box">
      <h3>{label}</h3>
      <div className="array-display">
        {values.map((val, idx) => {
          const classes = ['array-cell'];
          if (highlightIdx === idx && highlightType === 'current') classes.push('highlight-current');
          if (highlightIdx === idx && highlightType === 'popping') classes.push('highlight-popping');
          if (highlightIdx === idx && highlightType === 'answered') classes.push('highlight-answered');
          return (
            <div key={idx} className={classes.join(' ')}>
              <span className="day-label">{dayPrefix || 'Day'} {idx}</span>
              <span className="temp-value">{val}°C</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AnswerDisplay({ values, highlightIdx }) {
  if (!values || values.length === 0) return null;
  return (
    <div className="problem-box">
      <h3>Answer (wait days)</h3>
      <div className="array-display">
        {values.map((val, idx) => {
          const classes = ['array-cell'];
          if (highlightIdx === idx) classes.push('highlight-answered');
          return (
            <div key={idx} className={classes.join(' ')}>
              <span className="day-label">Day {idx}</span>
              <span className="answer-value">{val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StackVisual({ stack, temps, poppingIdx }) {
  if (!stack || stack.length === 0) {
    return <div className="stack-empty">Stack is empty</div>;
  }
  return (
    <div className="stack-visual">
      {stack.map((idx, i) => (
        <div key={idx} className={`stack-item${idx === poppingIdx ? ' popping' : ''}`}>
          <span className="stack-index">Index {idx}</span>
          <span>→</span>
          <span className="stack-temp">{temps[idx]}°C</span>
        </div>
      ))}
    </div>
  );
}

function AnswerVisual({ answer }) {
  if (!answer || answer.length === 0) return null;
  return (
    <div className="answer-visual">
      {answer.map((val, idx) => (
        <div key={idx} className="answer-item">
          Day {idx}: <strong>{val}</strong>
        </div>
      ))}
    </div>
  );
}

function StateInfo({ step, stepIndex, totalSteps }) {
  if (!step) return null;
  let badgeClass = 'processing';
  let badgeText = 'Processing';
  if (step.type === 'popping' || step.type === 'compare') {
    badgeClass = 'comparing';
    badgeText = 'Comparing & Popping';
  } else if (step.type === 'complete') {
    badgeClass = 'complete';
    badgeText = 'Complete';
  }
  return (
    <div className="state-info">
      <span className={`state-badge ${badgeClass}`}>{badgeText}</span>
      <span>Step {stepIndex + 1} / {totalSteps}</span>
      {step.currentTemp !== null && (
        <span>Current: <strong>Day {step.currentIdx} ({step.currentTemp}°C)</strong></span>
      )}
    </div>
  );
}

/* ===== Checkpoint Components ===== */

function Checkpoint1({ onLog }) {
  const [selected, setSelected] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const correctAnswer = 'A';

  const handleSelect = (opt) => {
    if (submitted) return;
    setSelected(opt);
  };

  const handleSubmit = () => {
    if (selected === null || submitted) return;
    setSubmitted(true);
    const isCorrect = selected === correctAnswer;
    onLog({
      type: 'checkpoint',
      correct: isCorrect,
      detail: `Checkpoint 1: Selected "${selected}" - ${isCorrect ? 'Correct!' : 'Incorrect.'} (Question about 75°C at index 2)`,
    });
  };

  const handleReset = () => {
    setSelected(null);
    setSubmitted(false);
  };

  return (
    <div className="checkpoint-card">
      <h2><span className="icon">🧪</span> Checkpoint 1: Predict the Operation</h2>
      <p className="checkpoint-desc">
        We are currently processing temperature <strong>75°C (index 2)</strong>. The stack currently contains indices 0 and 1 (corresponding to 73°C, 74°C). What will the next operation be?
      </p>
      <div className="options-list">
        {[
          { key: 'A', text: 'Pop the stack top and write to answer' },
          { key: 'B', text: 'Push the current index' },
        ].map((opt) => {
          let cls = 'option-btn';
          if (submitted && opt.key === correctAnswer) cls += ' correct';
          if (submitted && selected === opt.key && opt.key !== correctAnswer) cls += ' incorrect';
          if (selected === opt.key && !submitted) cls += ' selected';
          return (
            <button key={opt.key} className={cls} onClick={() => handleSelect(opt.key)} disabled={submitted}>
              <strong>{opt.key}.</strong> {opt.text}
            </button>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={submitted || selected === null}>
          Submit Answer
        </button>
        <button className="btn btn-outline btn-sm" onClick={handleReset} disabled={!submitted}>
          Retry
        </button>
      </div>
      {submitted && (
        <div className={`feedback-banner ${selected === correctAnswer ? 'correct' : 'incorrect'}`}>
          {selected === correctAnswer
            ? '✅ Correct! Since 75°C > 74°C (the stack top), we pop index 1 from the stack and write answer[1] = 2 - 1 = 1. Then we check again: 75°C > 73°C, so we also pop index 0 and write answer[0] = 2 - 0 = 2.'
            : '❌ Incorrect. Since 75°C is greater than the stack top (74°C), we must pop the stack first. The monotonic decreasing invariant requires that when a warmer temperature arrives, we resolve all colder pending days.'
          }
        </div>
      )}
    </div>
  );
}

function Checkpoint2({ onLog }) {
  const [selected, setSelected] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const correctAnswer = 'A';

  const handleSelect = (opt) => {
    if (submitted) return;
    setSelected(opt);
  };

  const handleSubmit = () => {
    if (selected === null || submitted) return;
    setSubmitted(true);
    const isCorrect = selected === correctAnswer;
    onLog({
      type: 'checkpoint',
      correct: isCorrect,
      detail: `Checkpoint 2: Selected "${selected}" - ${isCorrect ? 'Correct!' : 'Incorrect.'} (Question about monotonic property)`,
    });
  };

  const handleReset = () => {
    setSelected(null);
    setSubmitted(false);
  };

  return (
    <div className="checkpoint-card">
      <h2><span className="icon">🧪</span> Checkpoint 2: Stack Invariant</h2>
      <p className="checkpoint-desc">
        During the entire scan, regarding the state of the stack, which of the following is correct?
      </p>
      <div className="options-list">
        {[
          { key: 'A', text: 'The temperature values in the stack are monotonically decreasing' },
          { key: 'B', text: 'The temperature values in the stack are monotonically increasing' },
          { key: 'C', text: 'The temperatures corresponding to indices in the stack are in random order' },
        ].map((opt) => {
          let cls = 'option-btn';
          if (submitted && opt.key === correctAnswer) cls += ' correct';
          if (submitted && selected === opt.key && opt.key !== correctAnswer) cls += ' incorrect';
          if (selected === opt.key && !submitted) cls += ' selected';
          return (
            <button key={opt.key} className={cls} onClick={() => handleSelect(opt.key)} disabled={submitted}>
              <strong>{opt.key}.</strong> {opt.text}
            </button>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={submitted || selected === null}>
          Submit Answer
        </button>
        <button className="btn btn-outline btn-sm" onClick={handleReset} disabled={!submitted}>
          Retry
        </button>
      </div>
      {submitted && (
        <div className={`feedback-banner ${selected === correctAnswer ? 'correct' : 'incorrect'}`}>
          {selected === correctAnswer
            ? '✅ Correct! The monotonic decreasing stack is the key invariant. It ensures that for any two indices i < j in the stack, temperatures[i] > temperatures[j]. This guarantees that when a warmer day arrives, it is the "next warmer day" for all colder days at the top of the stack.'
            : '❌ Incorrect. The correct answer is A. The stack maintains a strictly decreasing order of temperatures. If indices i and j are in the stack with i below j (i was pushed earlier), then temperatures[i] > temperatures[j]. This is the monotonic decreasing property.'
          }
        </div>
      )}
    </div>
  );
}

function Checkpoint3({ onLog }) {
  const [sliderValue, setSliderValue] = useState(69);
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleSubmit = () => {
    if (submitted) return;
    setSubmitted(true);
    const testTemps = [73, 74, 75, 71, sliderValue, 72, 76, 73];
    let newWait = 0;
    for (let j = 5; j < testTemps.length; j++) {
      if (testTemps[j] > sliderValue) {
        newWait = j - 4;
        break;
      }
    }
    const originalWait = 1;
    const changed = newWait !== originalWait;
    onLog({
      type: 'checkpoint',
      correct: true,
      detail: `Checkpoint 3: Set day 4 temperature to ${sliderValue}°C. New wait days: ${newWait} (was ${originalWait}). ${changed ? 'Answer changed!' : 'Answer unchanged.'}`,
    });
    setFeedback({
      newWait,
      originalWait,
      changed,
      sliderValue,
    });
  };

  const handleReset = () => {
    setSliderValue(69);
    setSubmitted(false);
    setFeedback(null);
  };

  return (
    <div className="checkpoint-card">
      <h2><span className="icon">🧪</span> Checkpoint 3: Explore Sensitivity</h2>
      <p className="checkpoint-desc">
        Modify the temperature on <strong>day 4</strong> in the temperatures array from 69°C by dragging the slider. Predict how the waiting days on day 4 in answer will change, then submit to see the result.
      </p>
      <div className="slider-container">
        <span className="slider-label">Day 4 Temperature: <span className="slider-value">{sliderValue}°C</span></span>
        <input
          type="range"
          min="60"
          max="80"
          value={sliderValue}
          onChange={(e) => !submitted && setSliderValue(Number(e.target.value))}
          disabled={submitted}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', maxWidth: 320, fontSize: '0.75rem', color: '#718096' }}>
          <span>60°C</span>
          <span>80°C</span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={submitted}>
          Check Result
        </button>
        <button className="btn btn-outline btn-sm" onClick={handleReset} disabled={!submitted}>
          Retry
        </button>
      </div>
      {feedback && (
        <div className="feedback-banner correct" style={{ marginTop: 12 }}>
          {feedback.changed
            ? `📊 With day 4 at ${feedback.sliderValue}°C, the waiting days change from ${feedback.originalWait} to ${feedback.newWait}. The array becomes [73, 74, 75, 71, ${feedback.sliderValue}, 72, 76, 73]. Day 4 must now wait ${feedback.newWait} day(s) for a warmer temperature.`
            : `📊 With day 4 at ${feedback.sliderValue}°C, the waiting days remain ${feedback.originalWait}. The next warmer day (72°C at index 5) is still warmer than ${feedback.sliderValue}°C, so the answer doesn't change.`
          }
        </div>
      )}
    </div>
  );
}

function Checkpoint4({ onLog }) {
  const [revealed, setRevealed] = useState(false);

  const handleReveal = () => {
    setRevealed(true);
    onLog({
      type: 'checkpoint',
      correct: true,
      detail: 'Checkpoint 4: Revealed explanation about popping two indices at index 5 (72°C).',
    });
  };

  const explanationHtml = `✅ <strong>Explanation:</strong> The stack contains indices [2, 3, 4] corresponding to temperatures [75°C, 71°C, 69°C] (decreasing). When we encounter 72°C at index 5:
<br /><br />
1. Compare 72°C with stack top: 69°C (index 4). Since 72 > 69, pop index 4, write answer[4] = 5 - 4 = <strong>1</strong>.
<br />
2. Compare 72°C with new stack top: 71°C (index 3). Since 72 > 71, pop index 3, write answer[3] = 5 - 3 = <strong>2</strong>.
<br />
3. Compare 72°C with new stack top: 75°C (index 2). Since 72 <= 75, stop popping. Push index 5.
<br /><br />
Both indices were popped because 72°C is warmer than both 69°C and 71°C, making it the "next warmer day" for both pending days. The monotonic decreasing property ensures we only pop from the top while the current temperature exceeds the stack top.`;

  return (
    <div className="checkpoint-card">
      <h2><span className="icon">🧪</span> Checkpoint 4: Explain the Double Pop</h2>
      <p className="checkpoint-desc">
        In the trace, when processing temperature <strong>72°C (index 5)</strong>, indices 3 (71°C) and 4 (69°C) were popped successively. Why were two indices popped?
      </p>
      {!revealed ? (
        <button className="btn btn-outline btn-sm" onClick={handleReveal}>
          Reveal Explanation
        </button>
      ) : (
        <div className="feedback-banner correct" dangerouslySetInnerHTML={{ __html: explanationHtml }} />
      )}
    </div>
  );
}

/* ===== Main App ===== */
export default function App() {
  const trace = useRef(generateTrace(TEMPERATURES));
  const [stepIndex, setStepIndex] = useState(0);
  const [logEntries, setLogEntries] = useState([]);
  const [hintVisible, setHintVisible] = useState(false);
  const [answerVisible, setAnswerVisible] = useState(false);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const [speed, setSpeed] = useState(1000);
  const autoPlayRef = useRef(null);

  const steps = trace.current;
  const currentStep = steps[stepIndex];
  const totalSteps = steps.length;

  const addLog = useCallback((entry) => {
    setLogEntries((prev) => [
      ...prev,
      { time: formatTime(), ...entry },
    ]);
  }, []);

  // Log initial load
  useEffect(() => {
    addLog({ type: 'system', detail: 'Algorithm visualization loaded. Ready to begin.' });
  }, []);

  const handleStepForward = useCallback(() => {
    if (stepIndex < totalSteps - 1) {
      const next = stepIndex + 1;
      setStepIndex(next);
      addLog({ type: 'navigation', detail: `Advanced to step ${next + 1}: ${steps[next].message}` });
    }
  }, [stepIndex, totalSteps, steps, addLog]);

  const handleStepBack = useCallback(() => {
    if (stepIndex > 0) {
      const prev = stepIndex - 1;
      setStepIndex(prev);
      addLog({ type: 'navigation', detail: `Went back to step ${prev + 1}: ${steps[prev].message}` });
    }
  }, [stepIndex, steps, addLog]);

  const handleReset = useCallback(() => {
    setStepIndex(0);
    setAutoPlaying(false);
    setHintVisible(false);
    setAnswerVisible(false);
    addLog({ type: 'navigation', detail: 'Reset to initial state.' });
  }, [addLog]);

  const handleAutoPlay = useCallback(() => {
    if (autoPlaying) {
      setAutoPlaying(false);
      addLog({ type: 'navigation', detail: 'Auto-play stopped.' });
    } else {
      setAutoPlaying(true);
      addLog({ type: 'navigation', detail: `Auto-play started (speed: ${speed}ms).` });
    }
  }, [autoPlaying, speed, addLog]);

  // Auto-play effect
  useEffect(() => {
    if (autoPlaying) {
      autoPlayRef.current = setInterval(() => {
        setStepIndex((prev) => {
          if (prev >= totalSteps - 1) {
            setAutoPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, speed);
      return () => clearInterval(autoPlayRef.current);
    } else {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    }
  }, [autoPlaying, speed, totalSteps]);

  const handleHint = () => {
    setHintVisible(true);
    addLog({ type: 'hint', detail: 'Hint requested.' });
  };

  const handleShowAnswer = () => {
    setAnswerVisible(true);
    addLog({ type: 'answer', detail: 'Final answer revealed.' });
  };

  const handleLogCheckpoint = (entry) => {
    addLog(entry);
  };

  const isComplete = stepIndex >= totalSteps - 1;

  // Current displays
  const currentHighlightIdx = currentStep?.currentIdx ?? -1;
  const poppingIdx = currentStep?.poppedIdx ?? -1;
  const stackSnapshot = currentStep?.stackSnapshot ?? [];
  const answerSnapshot = currentStep?.answerSnapshot ?? new Array(TEMPERATURES.length).fill(0);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>🌡️ Daily Temperatures</h1>
        <p className="subtitle">Monotonic Stack • Interactive Algorithm Learning</p>
      </header>

      {/* Problem Card */}
      <div className="card">
        <h2><span className="icon">📋</span> Problem Statement</h2>
        <p style={{ marginBottom: 12, fontSize: '0.95rem' }}>
          An agricultural greenhouse has a series of future daily temperature forecasts. The administrator wants to know after each day how many days they must wait until a <strong>higher temperature</strong> occurs, in order to schedule automatic ventilation and shading strategies. If there is no future day with a higher temperature, the value for that position is <strong>0</strong>.
        </p>
        <div className="problem-grid">
          <ArrayDisplay
            label="Input Temperatures"
            values={TEMPERATURES}
            highlightIdx={stepIndex > 0 ? currentHighlightIdx : -1}
            highlightType={currentStep?.type === 'popping' || currentStep?.type === 'compare' ? 'popping' : 'current'}
            dayPrefix="Day"
          />
          <AnswerDisplay
            values={FINAL_ANSWER}
            highlightIdx={-1}
          />
        </div>
      </div>

      {/* Visualization Card */}
      <div className="card">
        <h2><span className="icon">🔍</span> Step-by-Step Visualization</h2>
        <StateInfo step={currentStep} stepIndex={stepIndex} totalSteps={totalSteps} />

        <div className="viz-section">
          <div className="viz-panel">
            <h3>📚 Monotonic Stack (indices)</h3>
            <StackVisual stack={stackSnapshot} temps={TEMPERATURES} poppingIdx={poppingIdx} />
          </div>
          <div className="viz-panel">
            <h3>📝 Current Answer Array</h3>
            <AnswerVisual answer={answerSnapshot} />
          </div>
        </div>

        {/* Current message */}
        {currentStep && (
          <div style={{
            marginTop: 12,
            padding: '10px 16px',
            background: '#edf2f7',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.9rem',
            fontStyle: 'italic',
            border: '1px solid #e2e8f0',
          }}>
            <strong>Action:</strong> {currentStep.message}
          </div>
        )}

        {/* Controls */}
        <div className="controls-row">
          <button className="btn btn-outline btn-sm" onClick={handleReset} disabled={stepIndex === 0 && !autoPlaying}>
            ⏮ Reset
          </button>
          <button className="btn btn-outline btn-sm" onClick={handleStepBack} disabled={stepIndex === 0 || autoPlaying}>
            ◀ Back
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleStepForward} disabled={isComplete || autoPlaying}>
            Next ▶
          </button>
          <button className={`btn btn-sm ${autoPlaying ? 'btn-warning' : 'btn-success'}`} onClick={handleAutoPlay}>
            {autoPlaying ? '⏸ Pause' : '▶ Auto Play'}
          </button>
          <div className="speed-control">
            <label htmlFor="speed-select">Speed:</label>
            <select
              id="speed-select"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              disabled={autoPlaying}
            >
              <option value={500}>Fast (0.5s)</option>
              <option value={1000}>Normal (1s)</option>
              <option value={2000}>Slow (2s)</option>
              <option value={3000}>Very Slow (3s)</option>
            </select>
          </div>
        </div>

        {/* Legend */}
        <div className="legend">
          <span className="legend-item"><span className="legend-swatch current"></span> Current Day</span>
          <span className="legend-item"><span className="legend-swatch popping"></span> Popping</span>
          <span className="legend-item"><span className="legend-swatch stack"></span> In Stack</span>
          <span className="legend-item"><span className="legend-swatch answered"></span> Answered</span>
        </div>
      </div>

      {/* Hint & Answer */}
      <div className="card">
        <h2><span className="icon">💡</span> Hints & Answer</h2>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn btn-outline btn-sm" onClick={handleHint}>
            {hintVisible ? '🟡 Hint Shown' : 'Show Hint'}
          </button>
          <button className="btn btn-outline btn-sm" onClick={handleShowAnswer}>
            {answerVisible ? '🔵 Answer Shown' : 'Show Final Answer'}
          </button>
        </div>
        {hintVisible && (
          <div className="reveal-box">
            <strong>💡 Hint:</strong> Use a <strong>monotonic decreasing stack</strong> to store indices of days that haven't found a warmer day yet. When you encounter a temperature that is warmer than the temperature at the top of the stack, pop from the stack and calculate the difference in indices. The stack ensures that temperatures are always in decreasing order from bottom to top. Days that never find a warmer temperature stay in the stack and get answer 0.
          </div>
        )}
        {answerVisible && (
          <div className="reveal-box answer">
            <strong>🔵 Final Answer:</strong> <code style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem' }}>[1, 1, 4, 2, 1, 1, 0, 0]</code>
            <br /><br />
            <strong>Strategy Summary:</strong> Maintain a monotonic decreasing stack of indices. Iterate through temperatures left to right. For each temperature, while the stack is not empty and the current temperature is greater than the temperature at the stack's top index, pop the top index j and set answer[j] = currentIndex - j. Then push the current index. After the loop, all remaining indices in the stack have answer 0.
          </div>
        )}
      </div>

      {/* Checkpoints */}
      <Checkpoint1 onLog={handleLogCheckpoint} />
      <Checkpoint2 onLog={handleLogCheckpoint} />
      <Checkpoint3 onLog={handleLogCheckpoint} />
      <Checkpoint4 onLog={handleLogCheckpoint} />

      {/* Learning Log */}
      <div className="card">
        <h2><span className="icon">📜</span> Activity / Learning Log</h2>
        {logEntries.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>No activity yet. Start exploring the visualization or answer a checkpoint.</p>
        ) : (
          <ul className="log-list">
            {logEntries.map((entry, i) => (
              <li key={i}>
                <span className="log-time">{entry.time}</span>
                <span className="log-icon">
                  {entry.type === 'navigation' ? '🔹' :
                   entry.type === 'checkpoint' ? (entry.correct ? '✅' : '❌') :
                   entry.type === 'hint' ? '💡' :
                   entry.type === 'answer' ? '🔵' :
                   '📌'}
                </span>
                <span className="log-msg">{entry.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
