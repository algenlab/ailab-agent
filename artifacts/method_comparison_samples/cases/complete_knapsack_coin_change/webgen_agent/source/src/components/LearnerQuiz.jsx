import React, { useState } from 'react'

function QuizCard({ question, state, history, onSubmit, onHint, onShowAnswer }) {
  const [inputValue, setInputValue] = useState('')
  const [showHint, setShowHint] = useState(false)
  const submitted = state?.submitted
  const isCorrect = state?.isCorrect
  const revealed = state?.revealed

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onSubmit(question.id, inputValue.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }

  const handleHintClick = () => {
    setShowHint(true)
    onHint(question.id)
  }

  const feedbackStyle = isCorrect === true
    ? { background: '#f0fff4', border: '2px solid #68d391', color: '#276749' }
    : isCorrect === false
      ? { background: '#fff5f5', border: '2px solid #fc8181', color: '#9b2c2c' }
      : revealed
        ? { background: '#ebf8ff', border: '2px solid #63b3ed', color: '#2b6cb0' }
        : {}

  return (
    <div style={styles.card}>
      <div style={styles.qHeader}>
        <span style={styles.qNum}>问题 #{question.id}</span>
        {history === true && <span style={styles.correctBadge}>✅ 已答对</span>}
        {history === false && <span style={styles.incorrectBadge}>❌ 已答错</span>}
      </div>
      <p style={styles.qText}>{question.question}</p>

      {question.options ? (
        <div style={styles.optionsGrid}>
          {question.options.map(opt => (
            <button
              key={opt}
              style={{
                ...styles.optionBtn,
                background: submitted && String(inputValue) === opt
                  ? (isCorrect ? '#c6f6d5' : '#fed7d7')
                  : '#f7fafc',
                border: submitted && String(inputValue) === opt
                  ? (isCorrect ? '2px solid #68d391' : '2px solid #fc8181')
                  : '1px solid #e2e8f0',
              }}
              onClick={() => {
                if (!submitted) {
                  setInputValue(opt)
                }
              }}
              disabled={submitted}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <div style={styles.inputRow}>
          <input
            style={styles.textInput}
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的答案..."
            disabled={submitted}
          />
        </div>
      )}

      {!submitted && (
        <div style={styles.actionRow}>
          <button style={styles.submitBtn} onClick={handleSubmit} disabled={!inputValue.trim()}>
            提交答案
          </button>
          <button style={styles.hintBtn} onClick={handleHintClick}>
            💡 提示
          </button>
          <button style={styles.showAnswerBtn} onClick={() => onShowAnswer(question.id)}>
            👁️ 查看答案
          </button>
        </div>
      )}

      {showHint && !submitted && (
        <div style={styles.hintBox}>
          <strong>💡 提示：</strong>{question.explanation.slice(0, 120)}...
        </div>
      )}

      {submitted && (
        <div style={{ ...styles.feedbackBox, ...feedbackStyle }}>
          {isCorrect === true && <span>✅ 回答正确！</span>}
          {isCorrect === false && (
            <span>❌ 回答不正确。正确答案是：<strong>{question.answer}</strong></span>
          )}
          {revealed && <span>📖 正确答案是：<strong>{question.answer}</strong></span>}
          <p style={styles.explanation}>{question.fullExplanation || question.explanation}</p>
        </div>
      )}
    </div>
  )
}

export default function LearnerQuiz({ questions, quizState, quizHistory, onSubmit, onHint, onShowAnswer, allDone }) {
  return (
    <div style={styles.section}>
      <div style={styles.sectionHeader}>
        <h2 style={styles.sectionTitle}>🧠 学习者预测 / 检验</h2>
        {allDone && <span style={styles.allDoneBadge}>🎉 全部完成</span>}
      </div>
      <div style={styles.grid}>
        {questions.map(q => (
          <QuizCard
            key={q.id}
            question={q}
            state={quizState[q.id]}
            history={quizHistory[q.id]}
            onSubmit={onSubmit}
            onHint={onHint}
            onShowAnswer={onShowAnswer}
          />
        ))}
      </div>
    </div>
  )
}

const styles = {
  section: {
    background: '#fff',
    borderRadius: '16px',
    padding: '24px 32px',
    boxShadow: '0 2px 16px rgba(0,0,0,0.06)',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#1a202c',
  },
  allDoneBadge: {
    background: 'linear-gradient(135deg, #f0fff4, #e6fffa)',
    color: '#276749',
    padding: '4px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 700,
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  card: {
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '18px 20px',
    background: '#fafbfc',
  },
  qHeader: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    marginBottom: '8px',
  },
  qNum: {
    fontSize: '12px',
    fontWeight: 700,
    color: '#718096',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  correctBadge: {
    fontSize: '12px',
    color: '#276749',
    background: '#f0fff4',
    padding: '2px 10px',
    borderRadius: '10px',
    fontWeight: 600,
  },
  incorrectBadge: {
    fontSize: '12px',
    color: '#9b2c2c',
    background: '#fff5f5',
    padding: '2px 10px',
    borderRadius: '10px',
    fontWeight: 600,
  },
  qText: {
    fontSize: '15px',
    color: '#2d3748',
    lineHeight: 1.6,
    marginBottom: '12px',
  },
  optionsGrid: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  optionBtn: {
    padding: '8px 18px',
    fontSize: '14px',
    fontWeight: 600,
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  inputRow: {
    marginBottom: '14px',
  },
  textInput: {
    width: '100%',
    maxWidth: '360px',
    padding: '10px 14px',
    fontSize: '15px',
    border: '2px solid #e2e8f0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s',
    background: '#fff',
  },
  actionRow: {
    display: 'flex',
    gap: '14px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  submitBtn: {
    padding: '8px 20px',
    fontSize: '14px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
  },
  hintBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#4a5568',
    background: '#fffbeb',
    border: '1px solid #fbd38d',
    borderRadius: '8px',
    cursor: 'pointer',
  },
  showAnswerBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#4a5568',
    background: '#edf2f7',
    border: '1px solid #cbd5e0',
    borderRadius: '8px',
    cursor: 'pointer',
  },
  hintBox: {
    marginTop: '10px',
    padding: '10px 14px',
    background: '#fffbeb',
    border: '1px solid #fbd38d',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#744210',
    lineHeight: 1.5,
  },
  feedbackBox: {
    marginTop: '12px',
    padding: '12px 16px',
    borderRadius: '10px',
    fontSize: '14px',
    lineHeight: 1.6,
  },
  explanation: {
    marginTop: '6px',
    fontSize: '13px',
    opacity: 0.85,
  },
}