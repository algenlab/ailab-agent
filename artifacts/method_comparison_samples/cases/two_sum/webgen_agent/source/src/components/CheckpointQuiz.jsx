export default function CheckpointQuiz({
  questions,
  answers,
  feedback,
  activeHints,
  onAnswer,
  onHint,
  visible
}) {
  if (!visible) {
    return (
      <section className="quiz-section card">
        <div className="card-header">
          <span className="icon">📝</span> 测验问题
        </div>
        <div className="quiz-intro">
          🔒 请先完成算法可视化步骤（到达"已找到"状态）后解锁测验。
        </div>
      </section>
    )
  }

  return (
    <section className="quiz-section card">
      <div className="card-header">
        <span className="icon">📝</span> 测验问题
      </div>
      <div className="quiz-list">
        {questions.map((q) => {
          const answered = answers[q.id] !== undefined
          const fb = feedback[q.id]
          const hintShown = activeHints[q.id]
          const isCorrect = fb?.correct

          let itemClass = 'quiz-item'
          if (fb) {
            itemClass += fb.correct ? ' answered-correct' : ' answered-incorrect'
          }

          return (
            <div key={q.id} className={itemClass}>
              <div className="quiz-question-text">
                <strong>{q.id.toUpperCase()}.</strong> {q.question}
              </div>
              <div className="quiz-options">
                {q.options.map((opt, idx) => {
                  let optClass = 'quiz-option'
                  if (answered) optClass += ' locked'
                  if (fb) {
                    if (idx === q.correct) optClass += ' is-correct'
                    else if (idx === fb.selected && !fb.correct) optClass += ' is-incorrect'
                    else if (idx === q.correct) optClass += ' reveal-correct'
                  }
                  return (
                    <button
                      key={idx}
                      className={optClass}
                      onClick={() => !answered && onAnswer(q.id, idx)}
                      disabled={answered}
                    >
                      {opt}
                    </button>
                  )
                })}
              </div>

              {fb && (
                <div className={`quiz-feedback ${fb.correct ? 'correct' : 'incorrect'}`}>
                  {fb.correct ? '✅ 回答正确！' : '❌ 回答错误。'}
                  {' '}{q.explanation}
                </div>
              )}

              {!answered && !hintShown && (
                <button className="quiz-hint-btn" onClick={() => onHint(q.id)}>
                  💡 查看提示
                </button>
              )}

              {hintShown && !answered && (
                <div className="quiz-hint-text">
                  💡 {q.hint}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}