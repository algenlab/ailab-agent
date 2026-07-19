import React, { useState, useCallback } from 'react';
import { QuizQuestion, ActivityEntry } from '../types';
import { quizQuestions } from '../data';

interface Props {
  onActivity: (entry: Omit<ActivityEntry, 'id' | 'timestamp'>) => void;
}

interface QuestionState {
  selectedAnswer: string | null;
  isCorrect: boolean | null;
  isRevealed: boolean;
  hintUsed: boolean;
}

const QuizPanel: React.FC<Props> = ({ onActivity }) => {
  const [questionStates, setQuestionStates] = useState<Record<number, QuestionState>>(
    () => {
      const initial: Record<number, QuestionState> = {};
      quizQuestions.forEach((q) => {
        initial[q.id] = {
          selectedAnswer: null,
          isCorrect: null,
          isRevealed: false,
          hintUsed: false,
        };
      });
      return initial;
    }
  );

  const [numericInputs, setNumericInputs] = useState<Record<number, string>>({});

  const handleSelectOption = useCallback(
    (questionId: number, option: string, correctAnswer: string) => {
      const qs = questionStates[questionId];
      if (qs.isRevealed || qs.isCorrect !== null) return;

      const isCorrect = option === correctAnswer;
      setQuestionStates((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], selectedAnswer: option, isCorrect },
      }));

      onActivity({
        action: isCorrect ? '✅ 回答正确' : '❌ 回答错误',
        detail: `问题 ${questionId}：选择了 "${option}"`,
        type: 'answer',
      });
    },
    [questionStates, onActivity]
  );

  const handleNumericSubmit = useCallback(
    (questionId: number, correctAnswer: string) => {
      const qs = questionStates[questionId];
      if (qs.isRevealed || qs.isCorrect !== null) return;

      const input = numericInputs[questionId]?.trim() || '';
      const isCorrect = input === correctAnswer;

      setQuestionStates((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], selectedAnswer: input, isCorrect },
      }));

      onActivity({
        action: isCorrect ? '✅ 回答正确' : '❌ 回答错误',
        detail: `问题 ${questionId}：输入了 "${input}"`,
        type: 'answer',
      });
    },
    [numericInputs, questionStates, onActivity]
  );

  const handleHint = useCallback(
    (questionId: number) => {
      setQuestionStates((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], hintUsed: true },
      }));

      onActivity({
        action: '💡 使用提示',
        detail: `问题 ${questionId}：查看了提示`,
        type: 'hint',
      });
    },
    [onActivity]
  );

  const handleReveal = useCallback(
    (questionId: number) => {
      setQuestionStates((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], isRevealed: true },
      }));

      onActivity({
        action: '👁 查看答案',
        detail: `问题 ${questionId}：查看了正确答案`,
        type: 'reveal',
      });
    },
    [onActivity]
  );

  const handleResetQuestion = useCallback(
    (questionId: number) => {
      setQuestionStates((prev) => ({
        ...prev,
        [questionId]: {
          selectedAnswer: null,
          isCorrect: null,
          isRevealed: false,
          hintUsed: false,
        },
      }));
      setNumericInputs((prev) => ({ ...prev, [questionId]: '' }));

      onActivity({
        action: '🔄 重试',
        detail: `问题 ${questionId}：重新尝试`,
        type: 'system',
      });
    },
    [onActivity]
  );

  return (
    <div>
      {quizQuestions.map((q) => {
        const qs = questionStates[q.id];
        const showFeedback = qs.isCorrect !== null || qs.isRevealed;

        let containerClass = 'quiz-item';
        if (qs.isCorrect === true) containerClass += ' correct';
        else if (qs.isCorrect === false) containerClass += ' incorrect';
        else if (qs.isRevealed) containerClass += ' revealed';

        return (
          <div key={q.id} className={containerClass}>
            <div className="quiz-question">
              <strong>问题 {q.id}：</strong>
              {q.question}
            </div>

            {q.type === 'multiple-choice' && (
              <div className="quiz-options">
                {q.options.map((opt) => {
                  let optClass = 'quiz-option';
                  if (qs.selectedAnswer === opt) optClass += ' selected';
                  if (qs.isRevealed && opt === q.correctAnswer)
                    optClass += ' correct-answer';
                  if (
                    qs.isCorrect === false &&
                    qs.selectedAnswer === opt &&
                    opt !== q.correctAnswer
                  )
                    optClass += ' wrong-answer';

                  return (
                    <div
                      key={opt}
                      className={optClass}
                      onClick={() => {
                        if (!qs.isRevealed && qs.isCorrect === null) {
                          handleSelectOption(q.id, opt, q.correctAnswer);
                        }
                      }}
                    >
                      {opt}
                    </div>
                  );
                })}
              </div>
            )}

            {q.type === 'numeric' && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  className="quiz-input"
                  placeholder="输入数字答案..."
                  value={numericInputs[q.id] || ''}
                  onChange={(e) =>
                    setNumericInputs((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  disabled={qs.isRevealed || qs.isCorrect !== null}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleNumericSubmit(q.id, q.correctAnswer);
                    }
                  }}
                />
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => handleNumericSubmit(q.id, q.correctAnswer)}
                  disabled={qs.isRevealed || qs.isCorrect !== null}
                >
                  提交
                </button>
              </div>
            )}

            {/* Feedback */}
            {showFeedback && (
              <div
                className={`quiz-feedback ${
                  qs.isCorrect === true
                    ? 'correct-fb'
                    : qs.isCorrect === false
                    ? 'incorrect-fb'
                    : 'reveal-fb'
                }`}
              >
                {qs.isCorrect === true && (
                  <>
                    <strong>✅ 正确！</strong>{' '}
                    {qs.isRevealed ? q.explanation : '很好，你理解了算法的关键概念。'}
                  </>
                )}
                {qs.isCorrect === false && (
                  <>
                    <strong>❌ 不正确。</strong> 正确答案是：<strong>{q.correctAnswer}</strong>
                    <br />
                    {q.explanation}
                  </>
                )}
                {qs.isCorrect === null && qs.isRevealed && (
                  <>
                    <strong>📖 答案：</strong>
                    <strong>{q.correctAnswer}</strong>
                    <br />
                    {q.explanation}
                  </>
                )}
              </div>
            )}

            {/* Hint */}
            {qs.hintUsed && !qs.isRevealed && qs.isCorrect === null && (
              <div className="quiz-feedback reveal-fb">
                <strong>💡 提示：</strong>
                {q.hint}
              </div>
            )}

            {/* Actions */}
            <div className="quiz-actions">
              {!qs.isRevealed && qs.isCorrect === null && !qs.hintUsed && (
                <button
                  className="btn btn-sm"
                  onClick={() => handleHint(q.id)}
                >
                  💡 提示
                </button>
              )}
              {!qs.isRevealed && (
                <button
                  className="btn btn-sm"
                  onClick={() => handleReveal(q.id)}
                >
                  👁 显示答案
                </button>
              )}
              {(qs.isCorrect !== null || qs.isRevealed) && (
                <button
                  className="btn btn-sm"
                  onClick={() => handleResetQuestion(q.id)}
                >
                  🔄 重新尝试
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default QuizPanel;
