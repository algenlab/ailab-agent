import { useState } from 'react'

function renderSeen(seen) {
  const entries = Object.entries(seen)
  if (entries.length === 0) {
    return <div className="seen-empty">{'{} （空）'}</div>
  }
  return (
    <table className="seen-table">
      <thead>
        <tr>
          <th>值 (key)</th>
          <th>下标 (value)</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <td><strong>{key}</strong></td>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function getCellClass(index, state, foundIndices) {
  if (foundIndices && foundIndices.includes(index)) return 'array-cell found'
  if (state.phase === 'init') return 'array-cell'
  if (state.phase === 'found' && index === state.index) return 'array-cell found'
  if (state.phase === 'found' && index === foundIndices?.[0]) return 'array-cell found'
  if (index === state.index + 1 && state.phase === 'processed') return 'array-cell current'
  if (index === state.index && state.phase === 'processed') return 'array-cell processed'
  if (index === state.index && state.phase !== 'init') return 'array-cell current'
  if (index < state.index) return 'array-cell processed'
  return 'array-cell'
}

export default function AlgorithmVisualizer({
  state,
  stateIndex,
  totalStates,
  nums,
  onNext,
  onPrev,
  canGoNext,
  canGoPrev,
  checkpointActive,
  checkpointFeedback,
  onCheckpointAnswer,
  onSkipCheckpoint,
  predictionOptions,
  predictionCorrect,
  showHint,
  onShowHint,
  isComplete
}) {
  const [selectedOption, setSelectedOption] = useState(null)

  const foundIndices = state.result || null

  const handleOptionClick = (optionId) => {
    if (checkpointFeedback) return
    setSelectedOption(optionId)
    onCheckpointAnswer(optionId)
  }

  return (
    <section className="visualizer card">
      <div className="card-header">
        <span className="icon">🔍</span> 算法可视化
      </div>

      {/* Step indicator */}
      <div className="vis-step-indicator">
        <span>步骤</span>
        <div className="step-dots">
          {Array.from({ length: totalStates }, (_, i) => (
            <div
              key={i}
              className={`step-dot ${i === stateIndex ? 'active' : ''} ${i < stateIndex ? 'done' : ''}`}
            />
          ))}
        </div>
        <span className="step-label">
          {stateIndex + 1} / {totalStates}
          {stateIndex === 0 && ' — 初始化'}
          {state.phase === 'processed' && ' — 扫描中'}
          {state.phase === 'found' && ' — 已找到'}
        </span>
      </div>

      {/* Array visualization */}
      <div className="vis-array">
        {nums.map((val, idx) => (
          <div key={idx} className={getCellClass(idx, state, foundIndices)}>
            <span className="cell-index">i={idx}</span>
            <span className="cell-value">{val}</span>
          </div>
        ))}
      </div>

      {/* Info panels */}
      <div className="vis-info">
        <div className="vis-info-block">
          <strong>当前扫描</strong>
          {state.phase === 'init' ? (
            <span style={{ color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>尚未开始</span>
          ) : (
            <>
              <div>索引 i = <span className="mono">{state.index}</span></div>
              <div>nums[i] = <span className="mono">{state.currentVal}</span></div>
              <div>need = target - nums[i] = <span className="mono">{state.need}</span></div>
            </>
          )}
        </div>
        <div className="vis-info-block">
          <strong>哈希表 seen (操作前)</strong>
          {renderSeen(state.seenBefore)}
        </div>
      </div>

      {/* Description */}
      <div className={`vis-description ${state.phase === 'found' ? 'found-answer' : ''}`}>
        {state.description}
      </div>

      {/* Prediction Checkpoint */}
      {checkpointActive && (
        <div className="checkpoint-overlay">
          <div className="checkpoint-title">
            🔮 预测关卡
          </div>
          <div className="checkpoint-question">
            当算法处理到 <strong>i=1</strong>，<strong>nums[1]=7</strong>，seen 中已有{' '}
            <strong>{'{2: 0}'}</strong>。接下来会发生什么？
          </div>
          <div className="checkpoint-options">
            {predictionOptions.map(opt => {
              let cls = 'checkpoint-option'
              if (checkpointFeedback) {
                if (opt.id === predictionCorrect) {
                  cls += ' show-correct'
                }
                if (opt.id === checkpointFeedback.selected) {
                  cls += checkpointFeedback.correct ? ' selected-correct' : ' selected-incorrect'
                }
              }
              return (
                <button
                  key={opt.id}
                  className={cls}
                  onClick={() => handleOptionClick(opt.id)}
                  disabled={!!checkpointFeedback}
                >
                  <strong>{opt.id}</strong>) {opt.text}
                </button>
              )
            })}
          </div>
          {checkpointFeedback && (
            <div className={`checkpoint-feedback ${checkpointFeedback.correct ? 'correct' : 'incorrect'}`}>
              {checkpointFeedback.correct
                ? '✅ 回答正确！算法确实在 seen 中找到互补值 2，返回 [0, 1]。正在进入下一步...'
                : `❌ 不正确。正确答案是 A：计算 need=2，在 seen 中找到 2，返回 [0, 1]。正在进入下一步...`}
            </div>
          )}
          {!checkpointFeedback && (
            <button className="checkpoint-skip" onClick={onSkipCheckpoint}>
              跳过预测，直接查看结果 →
            </button>
          )}
        </div>
      )}

      {/* Hint */}
      {showHint && (
        <div className="vis-hint-text">
          💡 <strong>提示：</strong>在每一步中，算法计算 <code>need = target - nums[i]</code>，
          然后在哈希表 <code>seen</code> 中查找 <code>need</code>。如果找到，说明之前访问过的某个元素与当前元素之和为 target。
          如果没找到，就把当前元素值和下标存入 <code>seen</code>，继续扫描。
        </div>
      )}

      {/* Controls */}
      <div className="vis-controls">
        <button className="vis-btn" onClick={onPrev} disabled={!canGoPrev}>
          ◀ 上一步
        </button>
        <button className="vis-btn" onClick={onNext} disabled={!canGoNext || checkpointActive}>
          下一步 ▶
        </button>
        {!showHint && (
          <button className="vis-hint-btn" onClick={onShowHint}>
            💡 提示
          </button>
        )}
      </div>

      {isComplete && (
        <div className="completion-banner">
          🎉 算法执行完毕！在 i=1 时找到了解：nums[0] + nums[1] = 2 + 7 = 9 ✓
        </div>
      )}
    </section>
  )
}