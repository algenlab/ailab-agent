import React from 'react';

const HINTS = [
  'Trie（前缀树）的每个节点存储一个 count，表示有多少个单词经过该节点。',
  '插入单词时，沿路径每个节点 count+1。插入 "apple" 时，根节点→a→p→p→l→e，每个节点 count 都+1。',
  '查询时，只需沿 prefix 字符路径走到对应节点，该节点的 count 就是答案。',
  '如果 prefix 的某个字符在当前节点找不到子节点，说明没有单词匹配该前缀，答案为 0。',
  '当前示例中，插入 apple、app、ape 后，节点 "p"（路径 a→p）的 count=3，因为三个单词都经过它。',
  'bat 不经过 a→p 路径，所以不影响节点 "p" 的 count。',
  '最终沿 a→p 路径走到节点 "p"，其 count=3，即为答案。',
  '观察可视化图中节点的 count 值：根节点 count=4（共4个单词），节点 a count=3，节点 p count=3。',
  '思考题：如果新增单词 "apx"，prefix 仍为 "ap"，答案会变成 4，因为 a→p 路径上 count 增至 4。',
];

export default function HintPanel({ currentStep, onDismiss }) {
  const hintIndex = Math.min(currentStep, HINTS.length - 1);
  const hint = HINTS[hintIndex] || HINTS[HINTS.length - 1];

  return (
    <div className="card hint-panel">
      <div className="card-header">💡 提示</div>
      <div className="hint-content">{hint}</div>
      <button className="hint-dismiss" onClick={onDismiss}>
        关闭提示
      </button>
    </div>
  );
}
