import React from 'react';

export default function InputOutput({ nums, answer }) {
  return (
    <div className="card area-io">
      <div className="card-header">
        <div className="icon icon-blue">📋</div>
        <h2>题目数据</h2>
      </div>
      <div className="io-section">
        <div className="io-row">
          <span className="io-label">📥 输入 nums</span>
          <div className="io-value">
            <div className="io-array">
              {nums.map((n, i) => (
                <span key={i} className="io-chip io-chip-num">{n}</span>
              ))}
            </div>
          </div>
        </div>
        <div className="io-row">
          <span className="io-label">📤 最终答案（{answer.length} 个排列）</span>
          <div className="io-value">
            <div className="io-answer-grid">
              {answer.map((perm, i) => (
                <span key={i} className="io-perm-group">
                  [{perm.join(', ')}]
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
