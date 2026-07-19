import React, { useState, useMemo } from 'react';

function generateQuestion(state, nums, target) {
  const left = state.left;
  const right = state.right;
  const leftVal = nums[left];
  const rightVal = nums[right];
  const sum = state.sum;

  const questionText = `当前左指针下标 ${left}，价格 ${leftVal}，右指针下标 ${right}，价格 ${rightVal}，总和 ${sum}，target=${target}。下一步应移动哪个指针？`;
  
  const options = ['左指针右移（left++）', '右指针左移（right--）'];
  // If sum === target, no movement needed — found
  const correctIndex = sum < target ? 0 : 1;

  return { questionText, options, correctIndex };
}

export default function QuizPanel({ state, nums, target, quizState, quizResult, onStart, onAnswer, isComplete }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const currentQuestion = useMemo(() => {
    return generateQuestion(state, nums, target);
  }, [state, nums, target]);

  const handleOptionClick = (idx) => {
    if (submitted) return;
    setSelectedOption(idx);
  };

  const handleSubmit = () => {
    if (selectedOption === null || submitted) return;
    setSubmitted(true);
    const isCorrect = selectedOption === currentQuestion.correctIndex;
    const correctAnswer = currentQuestion.options[currentQuestion.correctIndex];
    onAnswer(currentQuestion.options[selectedOption], isCorrect, correctAnswer);
  };

  const handleStart = () => {
    setSelectedOption(null);
    setSubmitted(false);
    onStart();
  };

  const handleRetry = () => {
    setSelectedOption(null);
    setSubmitted(false);
  };

  // If algorithm is complete and found
  if (isComplete && state.found) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid #bbf7d0' }}>
        <p style={{ fontSize: '1.1rem', fontWeight: 600, color: '#15803d' }}>
          🎉 算法已完成！找到了匹配组合：[{state.left}, {state.right}]
        </p>
        <p style={{ fontSize: '0.9rem', color: '#166534', marginTop: 4 }}>
          nums[{state.left}]={nums[state.left]} + nums[{state.right}]={nums[state.right]} = {state.sum} = target
        </p>
      </div>
    );
  }

  if (isComplete && !state.found) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', background: '#fafafa', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
        <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          ⏹️ 搜索结束，未找到匹配组合（返回空列表）
        </p>
      </div>
    );
  }

  if (quizState === 'idle') {
    return (
      <div style={{ textAlign: 'center', padding: '8px 0' }}>
        <p style={{ marginBottom: 12, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          准备好了吗？测试你对指针移动方向的理解！
        </p>
        <button className="btn primary" onClick={handleStart}>
          📝 开始测验
        </button>
      </div>
    );
  }

  if (quizState === 'active') {
    return (
      <div className="quiz-block active">
        <div className="quiz-question">{currentQuestion.questionText}</div>
        <div className="quiz-options">
          {currentQuestion.options.map((opt, idx) => {
            let optClass = 'quiz-option';
            if (selectedOption === idx) optClass += ' selected';
            if (submitted && idx === currentQuestion.correctIndex) optClass += ' correct';
            if (submitted && selectedOption === idx && idx !== currentQuestion.correctIndex) optClass += ' incorrect';
            return (
              <button
                key={idx}
                className={optClass}
                onClick={() => handleOptionClick(idx)}
                disabled={submitted}
              >
                {opt}
              </button>
            );
          })}
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          {!submitted ? (
            <button className="btn primary" onClick={handleSubmit} disabled={selectedOption === null}>
              提交答案
            </button>
          ) : (
            <button className="btn" onClick={handleRetry}>
              🔄 再试一次
            </button>
          )}
        </div>
        {submitted && quizResult && (
          <div className={`feedback ${quizResult.correct ? 'correct' : 'incorrect'}`}>
            {quizResult.correct
              ? '✅ 回答正确！你理解了指针移动的规则。'
              : `❌ 回答错误。正确答案是：${quizResult.correctAnswer}。提示：sum < target 时需增大 sum，应移动左指针；sum > target 时需减小 sum，应移动右指针。`
            }
          </div>
        )}
      </div>
    );
  }

  // answered state - show summary
  return (
    <div style={{ padding: '12px 0' }}>
      {quizResult && (
        <div className={`feedback ${quizResult.correct ? 'correct' : 'incorrect'}`}>
          {quizResult.correct
            ? '✅ 上一次测验：回答正确！'
            : `❌ 上一次测验：选择了"${quizResult.selected}"，正确答案是"${quizResult.correctAnswer}"`
          }
        </div>
      )}
      <button className="btn primary" onClick={handleStart} style={{ marginTop: 8 }}>
        📝 重新测验
      </button>
    </div>
  );
}