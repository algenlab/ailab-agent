export default function ProblemDisplay({ nums, target, answer, showAnswer, onShowAnswer }) {
  return (
    <section className="problem-display card">
      <div className="card-header">
        <span className="icon">📦</span> 问题描述
      </div>
      <p style={{ marginBottom: 14, fontSize: '0.92rem', lineHeight: 1.7, color: 'var(--color-text)' }}>
        在订单配货系统中，<code>nums[i]</code> 表示第 <code>i</code> 个货位上可直接拣出的商品数量，
        订单还缺 <code>target</code> 件同类商品。找到两个不同货位，使它们的数量之和正好为 <code>target</code>，
        返回这两个货位的 <b>0-based 下标</b>；若不存在则返回空数组。
      </p>

      <div className="input-output">
        <div className="io-block">
          <h3>📥 输入 (Input)</h3>
          <div className="code-value">
            nums = [{nums.join(', ')}]
          </div>
          <div className="code-value" style={{ marginTop: 4 }}>
            target = {target}
          </div>
        </div>
        <div className="io-block">
          <h3>📤 期望输出 (Expected Output)</h3>
          <div className="code-value">
            {showAnswer ? `[${answer.join(', ')}]` : '???'}
          </div>
        </div>
      </div>

      <div className="answer-area">
        {!showAnswer ? (
          <button className="show-answer-btn" onClick={onShowAnswer}>
            👁️ 显示答案
          </button>
        ) : (
          <div className="answer-revealed">
            <span className="answer-label">✅ 答案：</span>
            <span className="answer-value">[{answer.join(', ')}]</span>
          </div>
        )}
      </div>
    </section>
  )
}