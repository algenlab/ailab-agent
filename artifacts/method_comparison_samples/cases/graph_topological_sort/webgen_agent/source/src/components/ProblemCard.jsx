import React from 'react';
import { INPUT_GRAPH, EXPECTED_ANSWER } from '../data';

export function ProblemCard() {
  return (
    <div className="card">
      <h2>📋 问题描述与输入/输出</h2>
      <div className="io-block">
        <div className="io-item">
          <div className="label">输入 (邻接表)</div>
          <pre>{JSON.stringify(INPUT_GRAPH, null, 2)}</pre>
        </div>
        <div className="io-item">
          <div className="label">期望输出 (最终答案)</div>
          <pre><span className="answer-highlight">{JSON.stringify(EXPECTED_ANSWER)}</span></pre>
        </div>
      </div>
    </div>
  );
}
