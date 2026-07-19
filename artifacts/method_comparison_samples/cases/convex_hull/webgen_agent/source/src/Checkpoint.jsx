import { useState } from 'react';

const CORRECT_ANSWER = 'A';

export default function Checkpoint({ logAction, checkpointStep, currentStep, state }) {
  const [selected, setSelected] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  const isEligible = currentStep >= checkpointStep;

  // Build dynamic options based on actual state
  const lowerBeforeStr = state?.lowerBefore
    ? state.lowerBefore.map(p => `(${p[0]},${p[1]})`).join(', ')
    : '';

  const lowerAfterAdd = state?.lowerAfter
    ? state.lowerAfter.map(p => `(${p[0]},${p[1]})`).join(', ')
    : '';

  const poppedPoint = state?.lowerBefore && state.lowerBefore.length >= 1
    ? state.lowerBefore[state.lowerBefore.length - 1]
    : null;
  const poppedStr = poppedPoint ? `(${poppedPoint[0]},${poppedPoint[1]})` : '';

  const options = [
    {
      id: 'A',
      text: `直接添加点 (1,2)，下凸壳变为 [${lowerAfterAdd || '(0,0),(1,1),(1,2)'}]`,
      correct: true,
    },
    {
      id: 'B',
      text: `弹出 ${poppedStr || '(1,1)'} 后添加，下凸壳变为 [(0,0),(1,2)]`,
      correct: false,
    },
    {
      id: 'C',
      text: `弹出 (0,0) 后添加，下凸壳变为 [${poppedStr || '(1,1)'},(1,2)]`,
      correct: false,
    },
  ];

  const handleSubmit = () => {
    if (!selected) return;
    setSubmitted(true);
    if (selected === CORRECT_ANSWER) {
      logAction('✅ 检查点回答正确：预测点 (1,2) 的处理正确');
    } else {
      logAction('❌ 检查点回答错误：对点 (1,2) 的处理预测不正确');
    }
  };

  const handleHint = () => {
    setShowHint(true);
    logAction('💡 查看了提示');
  };

  const handleShowAnswer = () => {
    setShowAnswer(true);
    logAction('👁 查看了答案');
  };

  return (
    <div className="checkpoint">
      <h3>🧪 学习检查点</h3>
      {!isEligible ? (
        <p className="info">请先浏览到步骤 <strong>{checkpointStep}</strong> 以激活此问题（当前步骤 {currentStep}）。</p>
      ) : (
        <>
          <p><strong>问题：</strong>在扫描线到达点 <strong>(1, 2)</strong> 时，下凸壳 <code>lower</code> 当前为 <code>[{lowerBeforeStr || '(0,0),(1,1)'}]</code>。根据 <code>cross</code> 计算结果，预测下一个 <code>lower</code> 状态是直接添加该点，还是弹出末尾点后再添加？为什么？</p>
          <div className="options">
            {options.map(opt => (
              <label
                key={opt.id}
                className={`option${submitted && opt.correct ? ' correct' : ''}${submitted && selected === opt.id && !opt.correct ? ' incorrect' : ''}`}
              >
                <input
                  type="radio"
                  name="checkpoint"
                  value={opt.id}
                  checked={selected === opt.id}
                  onChange={() => { if (!submitted) setSelected(opt.id); }}
                  disabled={submitted}
                />
                <span><strong>{opt.id})</strong> {opt.text}</span>
              </label>
            ))}
          </div>
          <div className="action-buttons">
            <button onClick={handleSubmit} disabled={!selected || submitted}>✓ 提交</button>
            <button className="btn-hint" onClick={handleHint}>💡 提示</button>
            <button className="btn-answer" onClick={handleShowAnswer}>👁 显示答案</button>
          </div>
          {submitted && (
            <div className={`feedback ${selected === CORRECT_ANSWER ? 'success' : 'error'}`}>
              {selected === CORRECT_ANSWER
                ? '✅ 正确！cross 值为正，表示左转，保持凸性，直接添加点 (1,2)。'
                : '❌ 不正确，请仔细分析 cross 值的符号含义后再试。'}
              {selected !== CORRECT_ANSWER && showAnswer && (
                <p>正确答案是 <strong>A</strong>：cross = 1 {'>'} 0 表示左转，凸性保持，无需回退。</p>
              )}
            </div>
          )}
          {showHint && (
            <div className="hint">
              <p>💡 <strong>提示：</strong>计算 cross product = (b - a) × (c - b)。设 a = (0,0), b = (1,1), c = (1,2)，则 cross = (1-0)×(2-1) - (1-0)×(1-1) = 1×1 - 1×0 = <strong>1</strong>。cross {'>'} 0 表示当前构成<strong>左转</strong>，凸性得以保持，因此无需弹出末尾点。</p>
            </div>
          )}
          {showAnswer && !submitted && (
            <div className="answer">
              <p><strong>正确答案：A)</strong> 直接添加点 (1,2)。因为 cross = 1 {'>'} 0（左转），凸性保持，下凸壳变为 [{(0,0)}, {(1,1)}, {(1,2)}]。</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}