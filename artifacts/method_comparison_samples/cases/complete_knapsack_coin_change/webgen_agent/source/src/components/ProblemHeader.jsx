import React from 'react'

export default function ProblemHeader() {
  return (
    <div style={styles.card}>
      <div style={styles.tagRow}>
        <span style={styles.tag}>DP 核心扩展</span>
        <span style={styles.tagSecondary}>完全背包</span>
      </div>
      <h1 style={styles.title}>完全背包零钱兑换</h1>
      <p style={styles.problem}>
        某商店收银员需要给顾客找零 <strong>amount</strong> 元。收银台中有无限数量的硬币，面额分别为数组 <strong>coins</strong>。
        请编写程序，计算收银员最少需要多少枚硬币才能凑出 <strong>amount</strong> 元。如果无论如何都无法凑出 <strong>amount</strong> 元，则返回 <strong>-1</strong>。
      </p>

      <div style={styles.objectives}>
        <h3 style={styles.objTitle}>📚 学习目标</h3>
        <ul style={styles.objList}>
          <li>理解 <code>dp[capacity]</code> 表示凑出容量 capacity 的最少硬币数</li>
          <li>分析 coin 循环和 capacity 正序递增如何允许硬币重复使用</li>
          <li>能够根据当前 dp 状态和硬币面额预测下一步 dp 更新</li>
        </ul>
      </div>

      <div style={styles.strategyBox}>
        <strong>⚡ 参考策略：</strong>
        正序容量更新 <code>dp[c]</code>，允许同一种硬币被重复使用。
        核心转移方程：<code>dp[c] = Math.min(dp[c], dp[c - coin] + 1)</code>
      </div>
    </div>
  )
}

const styles = {
  card: {
    background: '#fff',
    borderRadius: '16px',
    padding: '28px 32px',
    boxShadow: '0 2px 16px rgba(0,0,0,0.06)',
  },
  tagRow: { display: 'flex', gap: '10px', marginBottom: '14px' },
  tag: {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: '#fff',
    padding: '4px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 600,
  },
  tagSecondary: {
    background: '#edf2f7',
    color: '#4a5568',
    padding: '4px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 600,
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#1a202c',
    marginBottom: '12px',
  },
  problem: {
    fontSize: '15px',
    color: '#4a5568',
    lineHeight: 1.7,
    marginBottom: '18px',
  },
  objectives: {
    background: '#f7fafc',
    borderRadius: '12px',
    padding: '16px 20px',
    marginBottom: '14px',
  },
  objTitle: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#2d3748',
    marginBottom: '8px',
  },
  objList: {
    paddingLeft: '20px',
    fontSize: '14px',
    color: '#4a5568',
    lineHeight: 1.8,
  },
  strategyBox: {
    background: '#fffbeb',
    border: '1px solid #fbd38d',
    borderRadius: '10px',
    padding: '12px 18px',
    fontSize: '14px',
    color: '#744210',
  },
}