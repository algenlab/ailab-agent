import React, { useRef, useEffect } from 'react'

function formatVal(v) {
  if (v === Infinity) return '∞'
  return String(v)
}

function getCellStyle(capacity, stepCapacity, isUpdated, coin, amount) {
  const base = {
    width: '42px',
    height: '42px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 600,
    borderRadius: '8px',
    transition: 'all 0.2s ease',
    flexShrink: 0,
    position: 'relative',
  }

  if (capacity === stepCapacity && isUpdated) {
    return {
      ...base,
      background: 'linear-gradient(135deg, #fefcbf, #faf089)',
      border: '2px solid #ecc94b',
      color: '#744210',
      fontWeight: 800,
      transform: 'scale(1.08)',
      boxShadow: '0 0 12px rgba(236, 201, 75, 0.5)',
    }
  }
  if (capacity === stepCapacity && !isUpdated) {
    return {
      ...base,
      background: '#edf2f7',
      border: '2px solid #a0aec0',
      color: '#4a5568',
    }
  }
  return {
    ...base,
    background: '#f7fafc',
    border: '1px solid #e2e8f0',
    color: '#718096',
  }
}

export default function DpVisualization({ steps, stepIndex, onStepChange, onJumpToStep, coins, amount }) {
  const step = steps[stepIndex]
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      const activeEl = scrollRef.current.querySelector('[data-active="true"]')
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
      }
    }
  }, [stepIndex])

  const isFirst = stepIndex === 0
  const isLast = stepIndex === steps.length - 1

  const progressPct = Math.round(((stepIndex + 1) / steps.length) * 100)

  return (
    <div style={styles.card}>
      <div style={styles.headerRow}>
        <h2 style={styles.sectionTitle}>🔬 DP 状态可视化</h2>
        <span style={styles.stepBadge}>步骤 {stepIndex + 1} / {steps.length}</span>
      </div>

      {/* Progress bar */}
      <div style={styles.progressTrack}>
        <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
      </div>

      {/* Current step description */}
      <div style={{
        ...styles.descBox,
        background: step.type === 'final'
          ? 'linear-gradient(135deg, #f0fff4, #e6fffa)'
          : step.type === 'initial'
            ? '#f7fafc'
            : '#fffbeb'
      }}>
        <span style={styles.descIcon}>
          {step.type === 'final' ? '🏁' : step.type === 'initial' ? '🚀' : step.type === 'coin-start' ? '🪙' : step.type === 'coin-end' ? '✅' : '🔄'}
        </span>
        <span style={styles.descText}>{step.description}</span>
      </div>

      {/* Coin legend */}
      <div style={styles.coinLegend}>
        {coins.map(c => (
          <span key={c} style={{
            ...styles.coinLegendBadge,
            background: step.coin === c && (step.type === 'cell-update' || step.type === 'coin-start')
              ? '#fefcbf'
              : '#f7fafc',
            border: step.coin === c && (step.type === 'cell-update' || step.type === 'coin-start')
              ? '2px solid #ecc94b'
              : '1px solid #e2e8f0',
            fontWeight: step.coin === c && (step.type === 'cell-update' || step.type === 'coin-start') ? 800 : 500,
          }}>
            🪙 {c}元
          </span>
        ))}
      </div>

      {/* DP table scrollable */}
      <div style={styles.tableWrapper} ref={scrollRef}>
        <div style={styles.tableInner}>
          {/* header row: indices */}
          {Array.from({ length: amount + 1 }, (_, i) => (
            <div key={`h-${i}`} style={styles.indexCell}>
              {i}
            </div>
          ))}
          {/* value row */}
          {step.dp.map((val, i) => {
            const isActive = step.capacity === i
            const style = getCellStyle(i, step.capacity, step.updated, step.coin, amount)
            return (
              <div
                key={`v-${i}`}
                data-active={isActive || undefined}
                style={style}
                title={`dp[${i}] = ${formatVal(val)}`}
              >
                {formatVal(val)}
                {isActive && (
                  <div style={styles.activeIndicator}>▼</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Update detail card */}
      {step.type === 'cell-update' && (
        <div style={styles.updateCard}>
          <div style={styles.updateRow}>
            <span style={styles.updateLabel}>当前硬币</span>
            <span style={styles.updateValue}>{step.coin}元</span>
          </div>
          <div style={styles.updateRow}>
            <span style={styles.updateLabel}>容量</span>
            <span style={styles.updateValue}>capacity = {step.capacity}</span>
          </div>
          <div style={styles.updateRow}>
            <span style={styles.updateLabel}>dp[{step.capacity}] 旧值</span>
            <span style={styles.updateValue}>{formatVal(step.oldVal)}</span>
          </div>
          <div style={styles.updateRow}>
            <span style={styles.updateLabel}>dp[{step.fromCapacity}] + 1</span>
            <span style={styles.updateValue}>
              {formatVal(step.fromVal)} + 1 = {formatVal(step.candidate)}
            </span>
          </div>
          <div style={{ ...styles.updateRow, borderTop: '1px solid #e2e8f0', paddingTop: '8px', marginTop: '4px' }}>
            <span style={{ ...styles.updateLabel, fontWeight: 700 }}>新 dp[{step.capacity}]</span>
            <span style={{
              ...styles.updateValue,
              color: step.updated ? '#276749' : '#4a5568',
              fontWeight: 800,
              fontSize: '18px',
            }}>
              {formatVal(step.newVal)}
              {step.updated ? ' ✅' : ' (不变)'}
            </span>
          </div>
        </div>
      )}

      {/* Final answer highlight */}
      {step.type === 'final' && (
        <div style={styles.finalCard}>
          <span style={styles.finalLabel}>最终答案</span>
          <span style={styles.finalValue}>{step.finalAnswer}</span>
          <span style={styles.finalUnit}>枚硬币</span>
        </div>
      )}

      {/* Navigation controls */}
      <div style={styles.navRow}>
        <button
          style={{ ...styles.navBtn, opacity: isFirst ? 0.4 : 1, cursor: isFirst ? 'default' : 'pointer' }}
          onClick={() => onStepChange('prev')}
          disabled={isFirst}
        >
          ◀ 上一步
        </button>

        <div style={styles.navCenter}>
          <button
            style={{ ...styles.navBtnSmall, opacity: isFirst ? 0.4 : 1, cursor: isFirst ? 'default' : 'pointer' }}
            onClick={() => onJumpToStep(0)}
            disabled={isFirst}
          >
            ⏮ 开始
          </button>
          <span style={styles.navInfo}>{stepIndex + 1} / {steps.length}</span>
          <button
            style={{ ...styles.navBtnSmall, opacity: isLast ? 0.4 : 1, cursor: isLast ? 'default' : 'pointer' }}
            onClick={() => onJumpToStep(steps.length - 1)}
            disabled={isLast}
          >
            ⏭ 结束
          </button>
        </div>

        <button
          style={{ ...styles.navBtn, opacity: isLast ? 0.4 : 1, cursor: isLast ? 'default' : 'pointer' }}
          onClick={() => onStepChange('next')}
          disabled={isLast}
        >
          下一步 ▶
        </button>
      </div>

      {/* Quick step buttons */}
      <div style={styles.quickSteps}>
        <span style={styles.quickLabel}>快速跳转：</span>
        {steps.map((s, i) => {
          const isQuick = s.type === 'coin-start' || s.type === 'final'
          if (!isQuick) return null
          return (
            <button
              key={i}
              style={{
                ...styles.quickBtn,
                background: i === stepIndex ? '#667eea' : '#edf2f7',
                color: i === stepIndex ? '#fff' : '#4a5568',
              }}
              onClick={() => onJumpToStep(i)}
            >
              {s.type === 'final' ? '🏁' : `🪙${s.coin}`}
            </button>
          )
        })}
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
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#1a202c',
  },
  stepBadge: {
    background: '#edf2f7',
    color: '#4a5568',
    padding: '4px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 600,
  },
  progressTrack: {
    height: '4px',
    background: '#e2e8f0',
    borderRadius: '2px',
    marginBottom: '14px',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #667eea, #764ba2)',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  descBox: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
    padding: '12px 16px',
    borderRadius: '10px',
    marginBottom: '14px',
    fontSize: '14px',
    lineHeight: 1.6,
  },
  descIcon: { fontSize: '18px', flexShrink: 0, marginTop: '2px' },
  descText: { color: '#4a5568' },
  coinLegend: {
    display: 'flex',
    gap: '10px',
    marginBottom: '14px',
  },
  coinLegendBadge: {
    padding: '5px 12px',
    borderRadius: '8px',
    fontSize: '13px',
    transition: 'all 0.2s ease',
  },
  tableWrapper: {
    overflowX: 'auto',
    marginBottom: '14px',
    paddingBottom: '8px',
  },
  tableInner: {
    display: 'grid',
    gridTemplateColumns: `repeat(${12}, 42px)`,
    gap: '4px',
    minWidth: 'fit-content',
  },
  indexCell: {
    width: '42px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: 700,
    color: '#a0aec0',
  },
  activeIndicator: {
    position: 'absolute',
    top: '-18px',
    fontSize: '10px',
    color: '#ecc94b',
  },
  updateCard: {
    background: '#f7fafc',
    borderRadius: '10px',
    padding: '14px 18px',
    marginBottom: '14px',
  },
  updateRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
  },
  updateLabel: { fontSize: '13px', color: '#718096' },
  updateValue: { fontSize: '14px', fontWeight: 600, color: '#2d3748' },
  finalCard: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '10px',
    padding: '16px 20px',
    background: 'linear-gradient(135deg, #f0fff4, #e6fffa)',
    borderRadius: '12px',
    border: '2px solid #68d391',
    marginBottom: '14px',
  },
  finalLabel: { fontSize: '15px', fontWeight: 600, color: '#276749' },
  finalValue: { fontSize: '36px', fontWeight: 800, color: '#276749', lineHeight: 1 },
  finalUnit: { fontSize: '14px', color: '#4a5568' },
  navRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  navBtn: {
    padding: '10px 22px',
    fontSize: '14px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  navCenter: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  navBtnSmall: {
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#4a5568',
    background: '#edf2f7',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
  },
  navInfo: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#718096',
    minWidth: '50px',
    textAlign: 'center',
  },
  quickSteps: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '12px',
    flexWrap: 'wrap',
  },
  quickLabel: {
    fontSize: '12px',
    color: '#a0aec0',
    fontWeight: 600,
  },
  quickBtn: {
    padding: '5px 12px',
    fontSize: '12px',
    fontWeight: 600,
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
}