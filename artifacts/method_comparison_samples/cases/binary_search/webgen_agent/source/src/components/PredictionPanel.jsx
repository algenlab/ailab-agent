import React, { useState, useRef, useEffect } from 'react';
import './PredictionPanel.css';

const questions = [
  {
    id: 'q1',
    title: '📝 预测题 1：指针更新',
    question: '当前搜索区间 left=0, right=5, mid=2，nums=[-1,0,3,5,9,12]，target=9。nums[mid]=3 < target，下一步 left 和 right 将如何更新？',
    type: 'choice',
    options: [
      { id: 'a', text: 'left=0, right=2' },
      { id: 'b', text: 'left=3, right=5' },
      { id: 'c', text: 'left=2, right=5' },
      { id: 'd', text: 'left=0, right=4' }
    ],
    correct: 'b',
    explanation: '因为 nums[2]=3 < 9=target，目标在右半部分。更新 left = mid + 1 = 3，right 保持 5。新搜索区间为 [3, 5]。'
  },
  {
    id: 'q2',
    title: '📝 预测题 2：不变性',
    question: '在二分查找的任意步骤，关于搜索区间和 target 的关系，以下哪个陈述始终成立？',
    type: 'choice',
    options: [
      { id: 'a', text: 'A. target 一定在当前区间内' },
      { id: 'b', text: 'B. 如果 target 在数组中，则它一定在当前区间内' },
      { id: 'c', text: 'C. 区间长度总是偶数' },
      { id: 'd', text: 'D. left 一定小于 right' }
    ],
    correct: 'b',
    explanation: 'B 正确。二分查找的核心不变性（invariant）是：如果 target 存在于数组中，它一定在当前搜索区间 [left, right] 内。A 不对，因为 target 可能根本不在数组中。C 和 D 明显错误。'
  },
  {
    id: 'q3',
    title: '📝 预测题 3：早停条件',
    question: '假设 nums=[1,3,5,7,9]，target=4。修改 target 的值，使得查找过程能够"早停"（即循环次数少于原始查找）。请给出新的 target 值。',
    type: 'input',
    placeholder: '输入你选择的 target 值...',
    validate: (val) => {
      const n = parseInt(val);
      if (isNaN(n)) return { valid: false, message: '请输入一个整数' };
      return { valid: true };
    },
    checkCorrect: (val) => {
      const n = parseInt(val);
      return n === 5 || n === 1 || n === 7;
    },
    correctValues: [5, 1, 7],
    explanation: '原 target=4 需要经过 3 次比较（mid=5, mid=1, mid=3）。若选 target=5，第一次 mid=5 就匹配成功（仅 1 次循环）；若选 target=1 或 7，仅需 2 次循环。任何在数组中间位置的元素都比 4 查找次数少。'
  },
  {
    id: 'q4',
    title: '📝 预测题 4：构造反例',
    question: '某学生说："二分查找只要 nums 有序，无论是否有重复元素，都能正确返回任意一个 target 的索引。" 请构造一个反例 nums 和 target，用存在重复元素的数组证明该说法错误（假设要求返回 target 第一次出现的位置）。',
    type: 'input',
    placeholder: '输入 nums（逗号分隔），如: 1,2,2,3',
    validate: (val) => {
      const parts = val.split(',').map(s => s.trim()).filter(s => s !== '');
      if (parts.length === 0) return { valid: false, message: '请输入至少一个数字' };
      const nums = parts.map(Number);
      if (nums.some(isNaN)) return { valid: false, message: '请确保所有值都是数字' };
      const hasDup = new Set(nums).size < nums.length;
      if (!hasDup) return { valid: false, message: '数组需要包含重复元素（这是反例的关键）' };
      return { valid: true, parsed: nums };
    },
    checkCorrect: (val) => {
      const parts = val.split(',').map(s => s.trim()).filter(s => s !== '');
      const nums = parts.map(Number);
      const hasDup = new Set(nums).size < nums.length;
      if (!hasDup) return false;
      for (let i = 1; i < nums.length; i++) {
        if (nums[i] < nums[i-1]) return false;
      }
      return hasDup;
    },
    explanation: '例如 nums=[1,2,2,3], target=2。标准二分查找可能返回索引 2（第二个2），但第一次出现应该在索引 1。基本二分查找在遇到 mid 匹配时直接返回，无法保证返回的是第一次出现的位置。要找到第一次出现，需要对算法进行修改（如在找到后继续向左搜索）。'
  }
];

export default function PredictionPanel({
  nums, target, step, currentStep, addLog, isLastStep
}) {
  const [activeQuestion, setActiveQuestion] = useState(null);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [inputValues, setInputValues] = useState({});

  const questionRefs = useRef({});

  useEffect(() => {
    if (activeQuestion && questionRefs.current[activeQuestion]) {
      questionRefs.current[activeQuestion].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [feedback, activeQuestion]);

  const handleSelect = (qId, optionId) => {
    const q = questions.find(q => q.id === qId);
    const isCorrect = optionId === q.correct;
    setAnswers(prev => ({ ...prev, [qId]: optionId }));
    setFeedback(prev => ({
      ...prev,
      [qId]: { shown: true, correct: isCorrect, explanation: q.explanation }
    }));
    addLog(
      isCorrect ? 'correct' : 'incorrect',
      `${q.title}: ${isCorrect ? '✅ 正确！' : '❌ 错误'} 选择了 "${q.options.find(o => o.id === optionId).text}"`
    );
  };

  const handleInputSubmit = (qId) => {
    const q = questions.find(q => q.id === qId);
    const val = inputValues[qId] || '';
    const validation = q.validate(val);
    if (!validation.valid) {
      setFeedback(prev => ({
        ...prev,
        [qId]: { shown: true, correct: false, explanation: validation.message }
      }));
      return;
    }
    const isCorrect = q.checkCorrect(val);
    setAnswers(prev => ({ ...prev, [qId]: val }));
    setFeedback(prev => ({
      ...prev,
      [qId]: { shown: true, correct: isCorrect, explanation: q.explanation }
    }));
    addLog(
      isCorrect ? 'correct' : 'incorrect',
      `${q.title}: ${isCorrect ? '✅ 正确！' : '❌ 需要改进'} 输入了 "${val}"`
    );
  };

  const handleShowQuestion = (qId) => {
    setActiveQuestion(qId);
    setFeedback(prev => ({ ...prev, [qId]: { shown: false, correct: null, explanation: '' } }));
    setInputValues(prev => ({ ...prev, [qId]: '' }));
    setAnswers(prev => { const n = { ...prev }; delete n[qId]; return n; });
    addLog('navigation', `打开问题: ${questions.find(q => q.id === qId).title}`);
  };

  return (
    <div className="prediction-panel">
      <h3 className="section-title">🧠 学习者练习与预测</h3>
      <p className="prediction-hint">选择以下问题来测试你对二分查找的理解：</p>

      <div className="question-list">
        {questions.map(q => (
          <div
            key={q.id}
            className={`question-card ${activeQuestion === q.id ? 'active' : ''} ${feedback[q.id]?.shown ? (feedback[q.id]?.correct ? 'correct' : 'incorrect') : ''}`}
          >
            <div className="question-header" onClick={() => handleShowQuestion(q.id)}>
              <span className="question-title">{q.title}</span>
              <span className="question-toggle">{activeQuestion === q.id ? '▲' : '▶'}</span>
            </div>

            {activeQuestion === q.id && (
              <div className="question-body" ref={el => questionRefs.current[q.id] = el}>
                <p className="question-text">{q.question}</p>

                {q.type === 'choice' && (
                  <div className="options-list">
                    {q.options.map(opt => (
                      <button
                        key={opt.id}
                        className={`option-btn ${answers[q.id] === opt.id ? 'selected' : ''} ${feedback[q.id]?.shown && opt.id === q.correct ? 'correct' : ''} ${feedback[q.id]?.shown && answers[q.id] === opt.id && opt.id !== q.correct ? 'incorrect' : ''}`}
                        onClick={() => handleSelect(q.id, opt.id)}
                        disabled={feedback[q.id]?.shown}
                      >
                        {opt.text}
                      </button>
                    ))}
                  </div>
                )}

                {q.type === 'input' && (
                  <div className="input-answer-row">
                    <input
                      type="text"
                      className="answer-input"
                      placeholder={q.placeholder}
                      value={inputValues[q.id] || ''}
                      onChange={(e) => setInputValues(prev => ({ ...prev, [q.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === 'Enter' && handleInputSubmit(q.id)}
                      disabled={feedback[q.id]?.shown}
                    />
                    <button
                      className="btn btn-primary"
                      onClick={() => handleInputSubmit(q.id)}
                      disabled={feedback[q.id]?.shown}
                    >
                      提交
                    </button>
                  </div>
                )}

                {feedback[q.id]?.shown && (
                  <div className={`feedback-box ${feedback[q.id].correct ? 'feedback-correct' : 'feedback-incorrect'}`}>
                    <span className="feedback-icon">{feedback[q.id].correct ? '✅' : '❌'}</span>
                    <div>
                      <strong>{feedback[q.id].correct ? '回答正确！' : '回答不正确'}</strong>
                      <p>{feedback[q.id].explanation}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {isLastStep && (
        <div className="completion-banner">
          🎉 算法演示已完成！你已看到二分查找的完整过程。尝试回答上面的问题来巩固理解。
        </div>
      )}
    </div>
  );
}
