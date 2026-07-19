import React, { useState } from 'react';

const quizQuestions = [
  {
    id: 1,
    question: '回溯搜索中，当前 path 为 [1]，used 为 [True, False, False]，nums = [1,2,3]。按顺序遍历，下一个加入 path 的数字是什么？',
    options: ['1', '2', '3', '无法确定'],
    correctIndex: 1,
    explanation: 'used[0] 为 True（数字 1 已使用），按顺序检查 used[1] 为 False（数字 2 未使用），因此下一个选择是 nums[1]=2。',
    hints: [
      '提示 1：检查 used 数组，找到第一个为 False 的位置。',
      '提示 2：used[0]=True（已用），used[1]=False（未用），所以…',
    ],
  },
  {
    id: 2,
    question: '在生成全排列的过程中，path 的长度永远等于什么？',
    options: ['nums 的长度', '递归深度', '已使用数字的个数', '结果数组的长度'],
    correctIndex: 1,
    explanation: '每进入更深一层递归，path 长度加 1；每次回溯返回，path 长度减 1。因此 path.length 恒等于当前的递归深度。',
    hints: [
      '提示 1：观察每次 select 和 backtrack 时 path 长度如何变化。',
      '提示 2：path 长度随递归进入而增加，随递归返回而减少。',
    ],
  },
  {
    id: 3,
    question: "如果输入数组 nums 变为 ['a', 'b', 'c']（字符数组），回溯算法使用 used 基于下标，需要调整吗？",
    options: ['需要，字符不能比较', '需要，需改用哈希表', '不需要，下标索引与元素类型无关', '需要，要修改比较逻辑'],
    correctIndex: 2,
    explanation: 'used 数组基于下标（0, 1, 2）而非元素值来追踪使用状态，与元素类型无关。无论 nums 是数字、字符还是其他类型，算法逻辑不变。这体现了回溯算法的通用性。',
    hints: [
      '提示 1：used 数组追踪的是"位置"还是"值"？',
      '提示 2：used[i] 中的 i 是数组下标，与 nums[i] 的具体值无关。',
    ],
  },
  {
    id: 4,
    question: '对 nums=[1,2,3] 完成排列 [1,2,3] 后，执行 path.pop() 和 used[2]=False。这个状态转移过程被称为什么？',
    options: ['前进（Forward）', '回溯（Backtrack）', '剪枝（Pruning）', '递归（Recursion）'],
    correctIndex: 1,
    explanation: '从当前状态撤销最后一步选择（pop 移除 path 末尾，重置 used 标记），回到上一层状态以尝试其他可能性。这是回溯算法的核心操作——"回溯"（Backtrack）。',
    hints: [
      '提示 1：这个操作是"撤销选择，回到上一步"。',
      '提示 2：算法名称本身就包含了这个操作的描述。',
    ],
  },
];

export default function QuizPanel({ onLogEntry }) {
  const [quizState, setQuizState] = useState(() =>
    quizQuestions.map((q) => ({
      id: q.id,
      selectedOption: null,
      isCorrect: null,
      hintLevel: 0,
      showAnswer: false,
      locked: false,
    }))
  );

  function handleSelectOption(questionId, optionIndex) {
    setQuizState((prev) =>
      prev.map((qs) => {
        if (qs.id !== questionId || qs.locked) return qs;
        const question = quizQuestions.find((q) => q.id === questionId);
        const correct = optionIndex === question.correctIndex;
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

        onLogEntry({
          time: timeStr,
          type: correct ? 'correct' : 'incorrect',
          message: `问题${questionId}：选择了选项 "${question.options[optionIndex]}" — ${correct ? '✓ 正确' : '✗ 错误'}`,
        });

        return {
          ...qs,
          selectedOption: optionIndex,
          isCorrect: correct,
          locked: true,
        };
      })
    );
  }

  function handleHint(questionId) {
    setQuizState((prev) =>
      prev.map((qs) => {
        if (qs.id !== questionId || qs.locked) return qs;
        const question = quizQuestions.find((q) => q.id === questionId);
        const newLevel = qs.hintLevel + 1;
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

        onLogEntry({
          time: timeStr,
          type: 'hint',
          message: `问题${questionId}：查看提示 ${newLevel}`,
        });

        return {
          ...qs,
          hintLevel: Math.min(newLevel, question.hints.length),
        };
      })
    );
  }

  function handleShowAnswer(questionId) {
    setQuizState((prev) =>
      prev.map((qs) => {
        if (qs.id !== questionId || qs.locked) return qs;
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

        onLogEntry({
          time: timeStr,
          type: 'answer',
          message: `问题${questionId}：查看答案`,
        });

        return {
          ...qs,
          showAnswer: true,
          locked: true,
        };
      })
    );
  }

  return (
    <div className="card area-quiz">
      <div className="card-header">
        <div className="icon icon-purple">🧠</div>
        <h2>学习检测（4 题）</h2>
      </div>
      <div className="quiz-list">
        {quizQuestions.map((question) => {
          const state = quizState.find((qs) => qs.id === question.id);
          const isDone = state.locked;

          let itemClass = 'quiz-item';
          if (state.isCorrect === true) itemClass += ' correct';
          if (state.isCorrect === false) itemClass += ' incorrect';

          return (
            <div key={question.id} className={itemClass}>
              <div className="quiz-question">
                Q{question.id}. {question.question}
              </div>

              <div className="quiz-options">
                {question.options.map((opt, oi) => {
                  let optClass = 'quiz-option';
                  if (isDone && oi === question.correctIndex) {
                    optClass += ' revealed-correct';
                  }
                  if (state.selectedOption === oi && state.isCorrect === true) {
                    optClass += ' selected-correct';
                  }
                  if (state.selectedOption === oi && state.isCorrect === false) {
                    optClass += ' selected-incorrect';
                  }
                  if (isDone) optClass += ' disabled';
                  return (
                    <button
                      key={oi}
                      className={optClass}
                      onClick={() => handleSelectOption(question.id, oi)}
                      disabled={isDone}
                    >
                      {String.fromCharCode(65 + oi)}. {opt}
                    </button>
                  );
                })}
              </div>

              {/* Feedback */}
              {state.isCorrect === true && (
                <div className="quiz-feedback feedback-correct">
                  ✓ 正确！{question.explanation}
                </div>
              )}
              {state.isCorrect === false && (
                <div className="quiz-feedback feedback-incorrect">
                  ✗ 不正确。正确答案是：{question.options[question.correctIndex]}。{question.explanation}
                </div>
              )}

              {/* Hints */}
              {state.hintLevel > 0 && !isDone && (
                <div className="quiz-hint-text">
                  {question.hints[state.hintLevel - 1]}
                </div>
              )}

              {/* Show answer reveal */}
              {state.showAnswer && (
                <div className="quiz-answer-reveal">
                  💡 <strong>答案：</strong>{question.options[question.correctIndex]}
                  <br />
                  {question.explanation}
                </div>
              )}

              {/* Actions */}
              {!isDone && (
                <div className="quiz-actions">
                  <button
                    className="quiz-action-btn hint-btn"
                    onClick={() => handleHint(question.id)}
                    disabled={state.hintLevel >= question.hints.length}
                  >
                    💡 提示 {state.hintLevel > 0 ? `(${state.hintLevel}/${question.hints.length})` : ''}
                  </button>
                  <button
                    className="quiz-action-btn show-btn"
                    onClick={() => handleShowAnswer(question.id)}
                  >
                    👁 显示答案
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
