import React from 'react';

export default function ProblemDisplay({ m, n, answer }) {
  return (
    <div className="card" style={{ background: 'linear-gradient(135deg, #eff6ff 0%, #faf5ff 100%)', padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>🤖 不同路径</h2>
        <span className="badge">二维 DP</span>
      </div>
      
      <p style={{ fontSize: '0.88rem', lineHeight: 1.65, color: 'var(--text-secondary)', marginBottom: 10 }}>
        在一个 <strong>{m} 行 {n} 列</strong> 的智能仓库中，巡检机器人从左上角 
        <code style={{ background: '#e0e7ff', padding: '1px 6px', borderRadius: 3 }}>(0, 0)</code> 充电点出发，
        每次只能<strong>向右</strong>或<strong>向下</strong>移动一格。
        请计算机器人到达右下角 
        <code style={{ background: '#e0e7ff', padding: '1px 6px', borderRadius: 3 }}>({m - 1}, {n - 1})</code> 打包站的不同路径总数。
      </p>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ background: 'white', borderRadius: 'var(--radius)', padding: '8px 16px', border: '1px solid var(--border)', minWidth: 120 }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>📥 输入</span>
          <br />
          <span style={{ fontFamily: 'SF Mono, Fira Code, Fira Mono, monospace', fontSize: '1rem', fontWeight: 700 }}>
            m = {m}, n = {n}
          </span>
        </div>
        <div style={{ background: 'white', borderRadius: 'var(--radius)', padding: '8px 16px', border: '1px solid var(--border)', minWidth: 100 }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>📤 最终答案</span>
          <br />
          <span style={{ fontFamily: 'SF Mono, Fira Code, Fira Mono, monospace', fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)' }}>
            {answer}
          </span>
        </div>
        <div style={{ background: 'white', borderRadius: 'var(--radius)', padding: '8px 16px', border: '1px solid var(--border)', minWidth: 170 }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>📐 组合数验证</span>
          <br />
          <span style={{ fontFamily: 'SF Mono, Fira Code, Fira Mono, monospace', fontSize: '0.9rem', color: '#075985', fontWeight: 600 }}>
            C({m + n - 2}, {m - 1}) = {answer}
          </span>
        </div>
      </div>
    </div>
  );
}