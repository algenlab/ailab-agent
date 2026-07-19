import React from 'react';
import './ProblemHeader.css';

export default function ProblemHeader({ title, family, learningObjectives }) {
  return (
    <header className="problem-header">
      <div className="problem-header-top">
        <h1 className="problem-title">{title}</h1>
        <span className="problem-family">{family}</span>
      </div>
      <div className="problem-scenario">
        <p>
          你在图书馆工作，书架上有序排列着无重复索书号的书籍。给定书架数组 <code>nums</code>（每个位置 i 存放索书号 nums[i]），以及读者需要的目标索书号 <code>target</code>。请返回 <code>target</code> 所在的下标，如果不存在则返回 -1。
        </p>
      </div>
      <details className="learning-objectives">
        <summary><strong>🎯 学习目标</strong></summary>
        <ul>
          {learningObjectives.map((obj, i) => (
            <li key={i}>{obj}</li>
          ))}
        </ul>
      </details>
    </header>
  );
}
