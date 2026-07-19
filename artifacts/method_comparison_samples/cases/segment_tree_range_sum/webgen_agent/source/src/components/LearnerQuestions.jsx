import React, { useState } from 'react';
import './LearnerQuestions.css';

const QUESTIONS = [
  {
    id: 'q1',
    text: '线段树查询区间 query=[1,3] 时，当前访问节点 seg_0_1（覆盖 [0,1]，部分重叠），请问下一步应该访问哪两个子节点？',
    type: 'choice',
    options: [
      'seg_0_0 和 seg_1_1',
      'seg_1_1 和 seg_2_3',
      'seg_2_2 和 seg_3_3',
      'seg_0_0 和 seg_2_3',
    ],
    correctIndex: 0,
    hint: 'seg_0_1 的覆盖范围是 [0,1]，它的左右子节点分别覆盖 [0,0] 和 [1,1]。',
    answer: 'seg_0_0 和 seg_1_1 — 因为 seg_0_1 的左子覆盖 [0,0]，右子覆盖 [1,1]。',
  },
  {
    id: 'q2',
    text: '构建完成后，节点 seg_0_3 的 sum 为 12，其左子 seg_0_1 sum=3，右子 seg_2_3 sum=9，请写出三者之间满足的等式。',
    type: 'text',
    correctAnswer: '12=3+9',
    hint: '父节点的 sum 等于左右子节点 sum 之和。',
    answer: '12 = 3 + 9（即父节点 sum = 左子 sum + 右子 sum）',
  },
  {
    id: 'q3',
    text: '原题中 update=[2,6] 会把 nums[2] 从 4 改为 6，区间 [1,3] 的修正后和为 12。如果希望修正后区间和变成 15，应该把 update 的 value 改为多少？',
    type: 'choice',
    options: ['7', '8', '9', '10'],
    correctIndex: 2,
    hint: '修正后区间和 = 1（nums[1]）+ new_value + 5（nums[3]）= 15，解出 new_value。',
    answer: '9 — 因为 1 + value + 5 = 15，所以 value = 9。',
  },
  {
    id: 'q4',
    text: '构建线段树的叶子节点 seg_3_3 时，它的 sum 为什么等于 nums[3]？请用具体数组中的数值解释。',
    type: 'choice',
    options: [
      '因为 seg_3_3 的 l=3, r=3，叶子节点直接存储 nums[3]=5',
      '因为 seg_3_3 是所有节点的根',
      '因为 seg_3_3 存储的是它父节点的值',
      '因为 seg_3_3 是随机赋值的',
    ],
    correctIndex: 0,
    hint: '线段树叶子节点的特征是 l == r，此时节点代表单个数组元素。',
    answer: '因为 seg_3_3 的 l=3, r=3，叶子节点直接存储 nums[3]=5。',
  },
];

function ChoiceQuestion({ question, submitted, onSelect, selectedOption }) {
  return (
    <div className="question-options">
      {question.options.map((opt, i) => {
        let cls = 'q-option';
        if (submitted) {
          if (i === question.correctIndex) cls += ' q-option--correct';
          else if (i === selectedOption && i !== question.correctIndex) cls += ' q-option--wrong';
        } else if (i === selectedOption) {
          cls += ' q-option--selected';
        }
        return (
          <button
            key={i}
            className={cls}
            onClick={() => onSelect(i)}
            disabled={submitted}
          >
            <span className="q-option__marker">{String.fromCharCode(65 + i)}</span>
            <span>{opt}</span>
          </button>
        );
      })}
    </div>
  );
}

function TextQuestion({ question, submitted, onTextSubmit, feedback }) {
  const [value, setValue] = useState('');

  const handleSubmit = () => {
    if (value.trim()) {
      onTextSubmit(value.trim());
    }
  };

  return (
    <div className="question-text-input">
      <input
        type="text"
        className={`text-input ${submitted ? (feedback?.correct ? 'text-input--correct' : 'text-input--wrong') : ''}`}
        placeholder="输入你的答案..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
        disabled={submitted}
      />
      {!submitted && (
        <button className="btn btn-submit" onClick={handleSubmit} disabled={!value.trim()}>
          提交
        </button>
      )}
    </div>
  );
}

export default function LearnerQuestions({ questionStates, onQuestionSubmit, onShowHint, onShowAnswer, revealedAnswers }) {
  const [localSelections, setLocalSelections] = useState({});

  const handleSelect = (qId, q, index) => {
    setLocalSelections(prev => ({ ...prev, [qId]: index }));
    const correct = index === q.correctIndex;
    onQuestionSubmit(qId, correct, q.options[index]);
  };

  const handleTextSubmit = (qId, q, textValue) => {
    const correct = textValue.toLowerCase().replace(/\s/g, '') === q.correctAnswer.toLowerCase().replace(/\s/g, '');
    onQuestionSubmit(qId, correct, textValue);
  };

  return (
    <div className="learner-questions">
      {QUESTIONS.map((q, qi) => {
        const state = questionStates[q.id];
        const isRevealed = revealedAnswers.has(q.id);
        const selectedOpt = localSelections[q.id];

        return (
          <div key={q.id} className={`question-block ${state ? (state.correct ? 'question-block--correct' : 'question-block--wrong') : ''}`}>
            <div className="question-header">
              <span className="question-number">Q{qi + 1}</span>
              <span className="question-text">{q.text}</span>
            </div>

            {q.type === 'choice' ? (
              <ChoiceQuestion
                question={q}
                submitted={!!state}
                onSelect={(i) => handleSelect(q.id, q, i)}
                selectedOption={selectedOpt}
              />
            ) : (
              <TextQuestion
                question={q}
                submitted={!!state}
                onTextSubmit={(v) => handleTextSubmit(q.id, q, v)}
                feedback={state}
              />
            )}

            {state && (
              <div className={`question-feedback ${state.correct ? 'feedback--correct' : 'feedback--wrong'}`}>
                {state.correct ? '✅ 正确！' : `❌ 不正确。你回答的是"${state.learnerAnswer}"`}
              </div>
            )}

            <div className="question-actions">
              <button className="btn-action btn-hint" onClick={() => onShowHint(q.id, q.hint)}>
                💡 提示
              </button>
              <button className="btn-action btn-answer" onClick={() => onShowAnswer(q.id, q.answer)}>
                🔑 显示答案
              </button>
            </div>

            {isRevealed && (
              <div className="revealed-answer">
                <strong>答案：</strong>{q.answer}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
