
import React, { useState, useEffect } from 'react';

export default function QuizPanel({
  step,
  onCheck,
  onHint,
  onShowAnswer,
  feedback,
}) {
  const [takeVal, setTakeVal] = useState('');
  const [skipVal, setSkipVal] = useState('');

  useEffect(() => {
    if (step.showAnswerUsed) {
      setTakeVal(String(step.correctTake));
      setSkipVal(String(step.correctSkip));
    } else {
      setTakeVal('');
      setSkipVal('');
    }
  }, [step]);

  const handleCheck = () => {
    const t = parseInt(takeVal, 10);
    const s = parseInt(skipVal, 10);
    if (isNaN(t) || isNaN(s)) {
      alert('请输入有效的数字');
      return;
    }
    onCheck(t, s);
  };

  return (
    <div className="quiz-panel">
      <h4>🔮 预测节点 <strong>{step.nodeId}</strong> 的 DP 值</h4>
      <p>
        <strong>value({step.nodeId})</strong> = {step.value}
      </p>
      {step.children.length > 0 && (
        <div>
          <p>子节点已计算的 DP 值：</p>
          <ul>
            {step.children.map(c => (
              <li key={c.id}>
                节点 <strong>{c.id}</strong>: dp_take={c.dp_take}, dp_skip={c.dp_skip}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="quiz-inputs">
        <label>
          dp_take({step.nodeId}):
          <input
            type="number"
            value={takeVal}
            onChange={e => setTakeVal(e.target.value)}
            disabled={step.solved || step.showAnswerUsed}
            placeholder="?"
          />
        </label>
        <label>
          dp_skip({step.nodeId}):
          <input
            type="number"
            value={skipVal}
            onChange={e => setSkipVal(e.target.value)}
            disabled={step.solved || step.showAnswerUsed}
            placeholder="?"
          />
        </label>
      </div>
      {feedback && (
        <div className={`feedback ${feedback.status}`}>
          {feedback.message}
        </div>
      )}
      <div className="quiz-actions">
        <button onClick={handleCheck} disabled={takeVal === '' || skipVal === '' || step.solved}>
          ✓ 检查答案
        </button>
        <button onClick={onHint} disabled={step.solved}>
          💡 提示
        </button>
        <button onClick={onShowAnswer} disabled={step.solved}>
          👁 显示答案
        </button>
      </div>
      {step.solved && (
        <div className="solved-message">
          {step.showAnswerUsed
            ? '已显示答案，点击"下一步"继续算法执行'
            : '✓ 预测正确！点击"下一步"继续算法执行'}
        </div>
      )}
    </div>
  );
}
  