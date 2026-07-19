import React, { useState } from 'react';
import './QuizPanel.css';

function getCurrentParent(ufState) {
  return ufState.snapshot ? ufState.snapshot.parent : null;
}

function getStep(ufState) {
  return ufState.snapshot ? ufState.snapshot.step : -1;
}

export default function QuizPanel({ ufState, input, expectedAnswer, onAttempt, attempts }) {
  const [showHints, setShowHints] = useState({});
  const [showAnswers, setShowAnswers] = useState({});
  const [userAnswers, setUserAnswers] = useState({});
  const [feedback, setFeedback] = useState({});

  const parent = getCurrentParent(ufState);
  const step = getStep(ufState);

  function handleSelect(qId, value) {
    setUserAnswers(prev => ({ ...prev, [qId]: value }));
    setFeedback(prev => ({ ...prev, [qId]: null }));
  }

  function handleSubmit(qId, correctAnswer) {
    const userAnswer = userAnswers[qId];
    if (userAnswer === undefined || userAnswer === null || userAnswer === '') {
      setFeedback(prev => ({ ...prev, [qId]: { correct: false, msg: '请先选择一个选项。' } }));
      return;
    }
    const isCorrect = String(userAnswer) === String(correctAnswer);
    setFeedback(prev => ({
      ...prev,
      [qId]: {
        correct: isCorrect,
        msg: isCorrect ? '✅ 正确！' : '❌ 不正确，请再试一次。'
      }
    }));
    onAttempt(qId, isCorrect);
  }

  function toggleHint(qId) {
    setShowHints(prev => ({ ...prev, [qId]: !prev[qId] }));
  }

  function toggleAnswer(qId) {
    setShowAnswers(prev => ({ ...prev, [qId]: !prev[qId] }));
  }

  const questions = [
    {
      id: 1,
      title: '问题 1：预测 union 后 parent 数组变化',
      description: (
        <span>
          当前状态：处理到 <code>i=0, j=1</code>，<code>isConnected[0][1]=1</code>，
          且 <code>find(0)=0, find(1)=1</code>。<br />
          请预测执行 <code>union(0, 1)</code> 后 parent 数组会如何变化？
        </span>
      ),
      type: 'choice',
      options: [
        { value: 'A', label: 'parent[1] 变为 0，其余不变' },
        { value: 'B', label: 'parent[0] 变为 1，其余不变' },
        { value: 'C', label: 'parent[0] 和 parent[1] 都变为 0' },
        { value: 'D', label: 'parent 数组完全不变' }
      ],
      correctAnswer: 'A',
      hint: '回想并查集的 union 操作：将其中一个根节点指向另一个根节点。由于 find(0)=0 且 find(1)=1，它们分别是自己的根。按秩合并时，由于初始秩相等，会将第二个根指向第一个根（或相反，取决于实现），在此实现中 parent[1] 会被设置为 0。',
      explanation: '执行 union(0,1) 时，find(0)=0，find(1)=1，两者秩均为 0。按秩合并时 parent[1] 会被设置为 0（即 parent[1]=0），而 parent[0] 保持为 0。因此选 A。'
    },
    {
      id: 2,
      title: '问题 2：parent 数组的不变性',
      description: (
        <span>
          在整个算法过程中，parent 数组始终保持一个关键不变性。请选择正确的描述：
        </span>
      ),
      type: 'choice',
      options: [
        { value: 'A', label: '每个元素被指向的次数始终保持不变' },
        { value: 'B', label: 'parent 数组中不存在环路（即沿着 parent 走最终总能到达一个根节点）' },
        { value: 'C', label: 'parent[0] 始终等于 0' },
        { value: 'D', label: '所有 parent[i] 的值之和不变' }
      ],
      correctAnswer: 'B',
      hint: '并查集基于树结构，每个节点最多有一个父节点。如果存在环路，find 操作将陷入无限循环。路径压缩会改变 parent 值，但永远不会引入环。',
      explanation: 'parent 数组的本质是一组树（森林）。树结构的关键不变性是无环性——从任意节点出发沿着 parent 链前进，最终一定到达一个根节点（parent[i]=i 的节点）。路径压缩和按秩合并都不会破坏这个性质。'
    },
    {
      id: 3,
      title: '问题 3：修改矩阵预测省份数量',
      description: (
        <span>
          在给定的 isConnected 矩阵中，修改一个 0 为 1（但不要形成多连通区域），
          预测省份数量会如何改变？请给出修改后的矩阵与预期答案。
        </span>
      ),
      type: 'choice',
      options: [
        { value: 'A', label: '将 isConnected[0][2] 改为 1，预期省份数量为 1' },
        { value: 'B', label: '将 isConnected[1][2] 改为 1，预期省份数量为 1' },
        { value: 'C', label: '将 isConnected[1][2] 改为 1，预期省份数量仍为 2' },
        { value: 'D', label: '将 isConnected[0][2] 改为 1，预期省份数量为 0' }
      ],
      correctAnswer: 'A',
      hint: '原始矩阵中有 3 台计算机：0 和 1 已经连通（省份 1），2 是孤立的（省份 2）。如果将 isConnected[0][2] 改为 1，计算机 2 就会与省份 1 连通，从而省份总数从 2 降为 1。修改 isConnected[1][2] 同理。',
      explanation: '原始省份数为 2（{0,1} 和 {2}）。将 isConnected[0][2] 或 isConnected[1][2] 改为 1 都会使计算机 2 与省份 {0,1} 连通，从而所有三台计算机属于同一省份。预期答案变为 1。选 A 或 B 都合理（都连通到同一省份），此处 A 为参考答案。'
    },
    {
      id: 4,
      title: '问题 4：解释 union 操作的必要性',
      description: (
        <span>
          在追踪的过程中，步骤 step=3 执行了 union 操作。<br />
          请解释为何此时需要进行 union？它如何影响省份结构？
        </span>
      ),
      type: 'choice',
      options: [
        { value: 'A', label: '因为步骤 3 时 isConnected[0][1]=1 且两节点根不同，需要合并来减少省份数' },
        { value: 'B', label: '因为此时需要路径压缩来优化查找' },
        { value: 'C', label: '因为 rank 数组需要更新以保持树平衡' },
        { value: 'D', label: '因为所有节点必须最终指向同一个根' }
      ],
      correctAnswer: 'A',
      hint: 'union 操作的核心作用是将两个不同的集合合并为一个。步骤 3 中检测到 isConnected[0][1]=1（两台计算机直连），但它们当前的根节点不同（find(0)=0, find(1)=1），说明它们在两个不同的省份中，需要合并。',
      explanation: '当 isConnected[i][j]=1 且 find(i)≠find(j) 时，表示 i 和 j 直接连通但属于不同省份，必须执行 union 将它们合并为一个省份。合并后省份总数减 1。这是并查集解决"省份数量"问题的核心逻辑。'
    }
  ];

  return (
    <div className="card quiz-panel">
      <div className="card-header">
        <span>📝</span> 学习检测
        <span className="quiz-count">{questions.length} 道题</span>
      </div>

      <div className="quiz-list">
        {questions.map((q) => {
          const fb = feedback[q.id];
          const hintShown = showHints[q.id];
          const answerShown = showAnswers[q.id];

          return (
            <div key={q.id} className="quiz-item">
              <h4 className="quiz-title">{q.title}</h4>
              <p className="quiz-desc">{q.description}</p>

              <div className="quiz-options">
                {q.options.map((opt) => (
                  <label
                    key={opt.value}
                    className={`quiz-option ${
                      userAnswers[q.id] === opt.value ? 'option-selected' : ''
                    } ${
                      fb && fb.correct && userAnswers[q.id] === opt.value ? 'option-correct' : ''
                    } ${
                      fb && !fb.correct && userAnswers[q.id] === opt.value ? 'option-incorrect' : ''
                    }`}
                  >
                    <input
                      type="radio"
                      name={`q${q.id}`}
                      value={opt.value}
                      checked={userAnswers[q.id] === opt.value}
                      onChange={() => handleSelect(q.id, opt.value)}
                    />
                    <span className="option-label">{opt.value}. {opt.label}</span>
                  </label>
                ))}
              </div>

              <div className="quiz-actions">
                <button
                  className="quiz-btn quiz-btn-submit"
                  onClick={() => handleSubmit(q.id, q.correctAnswer)}
                >
                  提交答案
                </button>
                <button
                  className="quiz-btn quiz-btn-hint"
                  onClick={() => toggleHint(q.id)}
                >
                  💡 提示
                </button>
                <button
                  className="quiz-btn quiz-btn-answer"
                  onClick={() => toggleAnswer(q.id)}
                >
                  👁 查看答案
                </button>
              </div>

              {fb && (
                <div className={`quiz-feedback ${fb.correct ? 'feedback-correct' : 'feedback-incorrect'}`}>
                  {fb.msg}
                </div>
              )}

              {hintShown && (
                <div className="quiz-hint">
                  <strong>💡 提示：</strong>{q.hint}
                </div>
              )}

              {answerShown && (
                <div className="quiz-answer-reveal">
                  <strong>✅ 正确答案：</strong>{q.correctAnswer}
                  <br />
                  <strong>📖 解释：</strong>{q.explanation}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}