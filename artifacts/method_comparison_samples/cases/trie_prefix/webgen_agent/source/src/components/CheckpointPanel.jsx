import React from 'react';

const QUESTION = '在以上 Trie 插入完成后，prefix="ap" 最终能匹配到多少个单词？（请输入数字）';

export default function CheckpointPanel({ result, value, onValueChange, onSubmit, onRetry }) {
  let boxClass = 'card checkpoint-box';
  if (result === 'correct') boxClass += ' correct';
  if (result === 'incorrect') boxClass += ' incorrect';

  return (
    <div className={boxClass}>
      <div className="card-header">🎯 学习检测点</div>
      <p style={{ fontSize: '0.84rem', color: '#4a5568', lineHeight: 1.5, marginBottom: 8 }}>
        {QUESTION}
      </p>
      {result !== 'correct' && (
        <div className="checkpoint-input-row">
          <input
            className="checkpoint-input"
            type="text"
            inputMode="numeric"
            placeholder="输入你的预测…"
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSubmit();
            }}
            disabled={result === 'correct'}
          />
          <button
            className="checkpoint-submit"
            onClick={onSubmit}
            disabled={result === 'correct' || !value.trim()}
          >
            提交
          </button>
        </div>
      )}
      {result === 'correct' && (
        <div className="checkpoint-feedback correct">
          ✅ 回答正确！prefix="ap" 匹配 apple、app、ape 共 3 个单词。
        </div>
      )}
      {result === 'incorrect' && (
        <div>
          <div className="checkpoint-feedback incorrect">
            ❌ 回答错误。prefix="ap" 匹配的是 apple、app、ape，共 3 个单词。
          </div>
          <button className="checkpoint-retry" onClick={onRetry}>
            重新尝试
          </button>
        </div>
      )}
    </div>
  );
}
