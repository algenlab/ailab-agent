import React, { useState } from 'react'

export default function InputOutputDisplay({ input, expectedAnswer }) {
  const [showAnswer, setShowAnswer] = useState(false)

  return (
    <div style={styles.card}>
      <h2 style={styles.sectionTitle}>📋 具体输入 & 预期输出</h2>
      <div style={styles.grid}>
        <div style={styles.column}>
          <div style={styles.label}>输入 (JSON)</div>
          <pre style={styles.pre}>{JSON.stringify(input, null, 2)}</pre>
          <div style={styles.inputVisual}>
            <span style={styles.amountBadge}>amount = {input.amount}</span>
            <div style={styles.coinsRow}>
              {input.coins.map(c => (
                <span key={c} style={styles.coinBadge}>{c}元</span>
              ))}
              <span style={styles.infinite}>× ∞</span>
            </div>
          </div>
        </div>
        <div style={styles.divider} />
        <div style={styles.column}>
          <div style={styles.label}>预期输出</div>
          {showAnswer ? (
            <div style={styles.answerBox}>
              <span style={styles.answerValue}>{expectedAnswer}</span>
              <span style={styles.answerUnit}>枚硬币</span>
            </div>
          ) : (
            <button style={styles.revealBtn} onClick={() => setShowAnswer(true)}>
              👁️ 显示答案
            </button>
          )}
          <p style={styles.note}>
            <em>凑出 {input.amount} 元最少需要 {expectedAnswer} 枚硬币（5+5+1=11）</em>
          </p>
        </div>
      </div>
    </div>
  )
}

const styles = {
  card: {
    background: '#fff',
    borderRadius: '16px',
    padding: '24px 32px',
    boxShadow: '0 2px 16px rgba(0,0,0,0.06)',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#1a202c',
    marginBottom: '16px',
  },
  grid: {
    display: 'flex',
    gap: '24px',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
  },
  column: {
    flex: '1 1 240px',
    minWidth: '200px',
  },
  label: {
    fontSize: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#a0aec0',
    fontWeight: 600,
    marginBottom: '8px',
  },
  pre: {
    background: '#2d3748',
    color: '#e2e8f0',
    padding: '14px 18px',
    borderRadius: '10px',
    fontSize: '14px',
    fontFamily: "'SF Mono', 'Fira Code', 'Fira Mono', Menlo, Consolas, monospace",
    overflowX: 'auto',
    marginBottom: '12px',
  },
  inputVisual: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  amountBadge: {
    display: 'inline-block',
    background: '#ebf4ff',
    color: '#2b6cb0',
    padding: '6px 14px',
    borderRadius: '8px',
    fontWeight: 700,
    fontSize: '15px',
  },
  coinsRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  coinBadge: {
    display: 'inline-block',
    background: '#f0fff4',
    color: '#276749',
    padding: '6px 14px',
    borderRadius: '8px',
    fontWeight: 700,
    fontSize: '15px',
    border: '1px solid #c6f6d5',
  },
  infinite: {
    color: '#a0aec0',
    fontSize: '14px',
    fontWeight: 600,
  },
  divider: {
    width: '1px',
    alignSelf: 'stretch',
    background: '#e2e8f0',
    flexShrink: 0,
  },
  answerBox: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '8px',
    padding: '14px 20px',
    background: 'linear-gradient(135deg, #f0fff4, #e6fffa)',
    borderRadius: '12px',
    border: '2px solid #68d391',
  },
  answerValue: {
    fontSize: '40px',
    fontWeight: 800,
    color: '#276749',
    lineHeight: 1,
  },
  answerUnit: {
    fontSize: '16px',
    color: '#4a5568',
    fontWeight: 500,
  },
  revealBtn: {
    padding: '10px 24px',
    fontSize: '15px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
  },
  note: {
    marginTop: '10px',
    fontSize: '13px',
    color: '#a0aec0',
  },
}