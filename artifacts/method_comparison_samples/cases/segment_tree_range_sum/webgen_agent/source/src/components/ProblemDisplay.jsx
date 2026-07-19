import React from 'react';
import './ProblemDisplay.css';

function JSONDisplay({ data, label }) {
  return (
    <div className="json-display">
      <span className="json-label">{label}</span>
      <code className="json-value">{JSON.stringify(data)}</code>
    </div>
  );
}

export default function ProblemDisplay({ nums, query, update, finalAnswer }) {
  return (
    <div className="problem-display">
      <div className="problem-row">
        <JSONDisplay data={nums} label="nums" />
        <JSONDisplay data={query} label="query" />
        <JSONDisplay data={update} label="update" />
      </div>
      <div className="problem-divider">
        <span>↓ 线段树算法 ↓</span>
      </div>
      <div className="problem-row result-row">
        <JSONDisplay data={finalAnswer} label="最终答案" />
      </div>
    </div>
  );
}
