import React from 'react';

export default function ProblemInfo({ input, expectedOutput, description, objectives, strategy }) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="icon">📋</span>
        <h2>问题描述</h2>
      </div>
      <p className="problem-text">{description}</p>

      <div className="io-block">
        <span className="io-label">📥 输入 (Input)</span>
        <code className="io-value">{JSON.stringify(input)}</code>
      </div>
      <div className="io-block">
        <span className="io-label">📤 期望输出 (Expected Output)</span>
        <code className="io-value">{JSON.stringify(expectedOutput)}</code>
      </div>

      <div className="divider" />

      <div className="card-header">
        <span className="icon">🎯</span>
        <h2>学习目标</h2>
      </div>
      <ul className="objectives-list">
        {objectives.map((obj, i) => (
          <li key={i}>{obj}</li>
        ))}
      </ul>

      <div className="divider" />

      <div style={{ fontSize: '0.85rem', color: '#5a6170', fontStyle: 'italic' }}>
        <strong>参考策略：</strong>
        {strategy}
      </div>
    </div>
  );
}
