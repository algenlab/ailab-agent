import React, { useState, useMemo, useCallback } from 'react';
import { generateKMPSteps } from './algorithm/kmp';
import Visualizer from './components/Visualizer';
import Checkpoint from './components/Checkpoint';
import LearningLog from './components/LearningLog';
import JsonHighlight from './components/JsonHighlight';
import CopyButton from './components/CopyButton';

const INPUT_DATA = {
  pattern: "abc",
  text: "ababc"
};

const EXPECTED_RESULT = 2;

export default function App() {
  const { steps, result: computedResult } = useMemo(() => {
    return generateKMPSteps(INPUT_DATA.pattern, INPUT_DATA.text);
  }, []);

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [logEntries, setLogEntries] = useState([]);

  const addLogEntry = useCallback((entry) => {
    setLogEntries(prev => [...prev, { ...entry, timestamp: Date.now() }]);
  }, []);

  const handlePrev = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
      addLogEntry({
        type: 'navigation',
        direction: 'prev',
        step: currentStepIndex
      });
    }
  }, [currentStepIndex, addLogEntry]);

  const handleNext = useCallback(() => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
      addLogEntry({
        type: 'navigation',
        direction: 'next',
        step: currentStepIndex + 2
      });
    }
  }, [currentStepIndex, steps.length, addLogEntry]);

  const currentStep = steps[currentStepIndex];

  const isComplete = currentStep?.state?.matchStatus === 'found' || currentStep?.state?.matchStatus === 'not_found';

  const inputJsonString = JSON.stringify(INPUT_DATA, null, 2);

  return (
    <div className="app">
      <header className="app-header">
        <h1>KMP String Matching</h1>
        <span className="algorithm-family">Advanced String Algorithm</span>
      </header>

      <div className="main-layout">
        <div className="left-panel">
          {/* Problem Description */}
          <section className="problem-section">
            <h2>Problem</h2>
            <p>
              A genetic researcher is aligning a long DNA strand text and needs to quickly 
              find the first occurrence position of the target gene probe pattern. 
              Return <code>-1</code> if not found, or <code>0</code> if the pattern is an empty string. 
              The KMP algorithm builds a prefix table by analyzing the repetitive structure of the pattern itself, 
              achieving smart jumps during matching and avoiding naive character-by-character scanning from the beginning.
            </p>
          </section>

          {/* Input and Answer - side by side with equal height */}
          <div className="io-pair">
            <div className="io-box">
              <h3>Input</h3>
              <div className="io-pre-wrapper">
                <CopyButton text={inputJsonString} label="Copy" />
                <pre className="io-pre">
                  <JsonHighlight jsonString={inputJsonString} />
                </pre>
              </div>
            </div>
            <div className="io-box io-answer-box">
              <h3>Expected Answer</h3>
              <div className="io-pre-wrapper">
                <CopyButton text={JSON.stringify(EXPECTED_RESULT)} label="Copy" />
                <pre className="io-pre answer">{JSON.stringify(EXPECTED_RESULT)}</pre>
              </div>
              {isComplete && computedResult === EXPECTED_RESULT && (
                <div className="result-summary">
                  Algorithm result: {computedResult} — matches expected answer.
                </div>
              )}
              {isComplete && computedResult !== EXPECTED_RESULT && (
                <div className="result-summary not-found">
                  Algorithm result: {computedResult} — differs from expected answer.
                </div>
              )}
            </div>
          </div>

          {/* Learning Objectives */}
          <section className="objectives-section">
            <h3>Learning Objectives</h3>
            <ul>
              <li>Master the construction process of the prefix table pi in the KMP algorithm and its role in backtracking the j pointer upon mismatch</li>
              <li>Understand the pointer state changes of text and pattern during matching, and be able to predict the next operation based on the current state</li>
              <li>Be able to identify invariants in the matching process, such as the length of the matched prefix always equal to j</li>
            </ul>
          </section>

          {/* Algorithm Visualization */}
          <section className="viz-section-wrapper">
            <h2>Step-by-Step Visualization</h2>
            <Visualizer
              pattern={INPUT_DATA.pattern}
              text={INPUT_DATA.text}
              step={currentStep}
              stepIndex={currentStepIndex}
              totalSteps={steps.length}
              onPrev={handlePrev}
              onNext={handleNext}
            />
          </section>

          {/* Learning Log */}
          <LearningLog entries={logEntries} />
        </div>

        <div className="right-panel">
          <Checkpoint onLogEntry={addLogEntry} />
        </div>
      </div>
    </div>
  );
}