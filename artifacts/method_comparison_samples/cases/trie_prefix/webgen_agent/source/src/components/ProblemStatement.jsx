import React from 'react';

export default function ProblemStatement({ input, answer, showAnswer }) {
  return (
    <div className="card">
      <div className="card-header">📋 问题描述</div>
      <p style={{ fontSize: '0.88rem', color: '#4a5568', marginBottom: '12px', lineHeight: 1.6 }}>
        在一个搜索引擎的候选词库里，给定历史搜索词数组{' '}
        <code style={{ background: '#edf2f7', padding: '2px 6px', borderRadius: 4 }}>words</code>{' '}
        和用户当前输入的前缀字符串{' '}
        <code style={{ background: '#edf2f7', padding: '2px 6px', borderRadius: 4 }}>prefix</code>，
        请计算有多少个搜索词是以该前缀开头的。
      </p>
      <div className="problem-grid">
        <div className="problem-field">
          <span className="problem-label">Prefix</span>
          <span className="problem-value">{input.prefix}</span>
        </div>
        <div className="problem-field">
          <span className="problem-label">Words</span>
          <span className="problem-value">{JSON.stringify(input.words)}</span>
        </div>
      </div>
      <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ fontSize: '0.8rem', color: '#718096', fontWeight: 600 }}>最终答案：</span>
        {showAnswer ? (
          <span className="problem-answer">{answer}</span>
        ) : (
          <span className="problem-answer-hidden">?</span>
        )}
      </div>
    </div>
  );
}
