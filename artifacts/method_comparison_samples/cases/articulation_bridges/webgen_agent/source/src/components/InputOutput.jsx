import React from 'react';

export default function InputOutput({ input, expectedOutput, currentArticulation, currentBridges, isComplete }) {
  return (
    <div className="io-panel">
      <div className="io-section">
        <h3>📥 输入数据</h3>
        <pre className="io-code">{JSON.stringify(input, null, 2)}</pre>
      </div>

      <div className="io-section">
        <h3>📤 期望输出</h3>
        <pre className="io-code expected">{JSON.stringify(expectedOutput, null, 2)}</pre>
      </div>

      {(currentArticulation.length > 0 || currentBridges.length > 0 || isComplete) && (
        <div className="io-section">
          <h3>🔬 当前算法结果</h3>
          <div className={`current-result ${isComplete ? 'result-complete' : 'result-partial'}`}>
            <div>
              <strong>割点: </strong>
              <span className="result-value">
                [{currentArticulation.join(', ')}]
                {isComplete && arraysEqual(currentArticulation.sort(), expectedOutput.articulation.sort()) &&
                  <span className="match-badge match">✓ 匹配</span>
                }
                {isComplete && !arraysEqual(currentArticulation.sort(), expectedOutput.articulation.sort()) &&
                  <span className="match-badge no-match">✗ 不匹配</span>
                }
              </span>
            </div>
            <div>
              <strong>桥: </strong>
              <span className="result-value">
                [{currentBridges.map(([u, v]) => `(${u},${v})`).join(', ')}]
                {isComplete && bridgesEqual(currentBridges, expectedOutput.bridges) &&
                  <span className="match-badge match">✓ 匹配</span>
                }
                {isComplete && !bridgesEqual(currentBridges, expectedOutput.bridges) &&
                  <span className="match-badge no-match">✗ 不匹配</span>
                }
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, i) => v === sb[i]);
}

function bridgesEqual(a, b) {
  if (a.length !== b.length) return false;
  const norm = (arr) => arr.map(([u, v]) => [u, v].sort().join(',')).sort();
  return norm(a).every((v, i) => v === norm(b)[i]);
}