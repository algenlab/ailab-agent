import React from 'react';

const STEPS = [
  '维护入度表 indegree — 记录每门课还有多少门前导课未修',
  '找出所有 indegree = 0 的节点，加入队列 queue',
  '从队列头部弹出一个节点，加入结果列表',
  '遍历该节点的所有邻居，将它们的 indegree 减 1',
  '若某邻居 indegree 变为 0，则将其加入队列',
  '重复步骤 3-5，直到队列为空'
];

export function StrategyCard() {
  return (
    <div className="card">
      <h2>🧠 参考策略 (Kahn 算法)</h2>
      <ul className="strategy-list">
        {STEPS.map((s, i) => (
          <li key={i}>
            <span className="step-num">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
