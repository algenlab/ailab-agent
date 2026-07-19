import React from 'react';
import './ProblemDisplay.css';

export default function ProblemDisplay({ input, expectedAnswer }) {
  return (
    <div className="card problem-display">
      <div className="card-header">
        <span className="header-icon">📋</span> 问题描述与数据
      </div>

      <div className="problem-body">
        <p className="problem-desc">
          在一个大型企业网络中，计算机之间的物理连接由对称矩阵 <code>isConnected</code> 表示，
          其中 <code>isConnected[i][j] = 1</code> 表示计算机 <code>i</code> 与 <code>j</code> 直接连通。
          如果两台计算机通过一系列直接连接能够互通，则它们属于同一个<strong>省份</strong>。
          请计算网络中不同省份的总数。
        </p>

        <div className="data-section">
          <h4>输入数据 (isConnected)</h4>
          <div className="matrix-display">
            {input.isConnected.map((row, i) => (
              <div key={i} className="matrix-row">
                <span className="matrix-label">计算机 {i}:</span>
                <div className="matrix-cells">
                  {row.map((val, j) => (
                    <span
                      key={j}
                      className={`matrix-cell ${val === 1 ? 'cell-connected' : 'cell-disconnected'}`}
                      title={`isConnected[${i}][${j}] = ${val}`}
                    >
                      {val}
                      {i === j && <span className="cell-self-badge">S</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="answer-section">
          <span className="answer-label">预期答案：</span>
          <span className="answer-value">{expectedAnswer} 个省份</span>
        </div>
      </div>
    </div>
  );
}