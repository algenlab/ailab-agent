
import React from 'react';

export default function DPStateTable({ nodeIds, values, dpTake, dpSkip }) {
  const allDone = nodeIds.every(id => dpTake[id] !== undefined && dpSkip[id] !== undefined);

  return (
    <div className="dp-table-container">
      <h4>DP 状态表 {allDone && <span className="table-done-badge">✓ 全部完成</span>}</h4>
      <table className="dp-table">
        <thead>
          <tr>
            <th>节点</th>
            <th>value</th>
            <th>dp_take</th>
            <th>dp_skip</th>
            <th>max</th>
          </tr>
        </thead>
        <tbody>
          {nodeIds.map(id => {
            const t = dpTake[id];
            const s = dpSkip[id];
            const maxVal = (t !== undefined && s !== undefined) ? Math.max(t, s) : undefined;
            return (
              <tr key={id}>
                <td><strong>{id}</strong></td>
                <td>{values[id]}</td>
                <td className={t !== undefined ? 'computed' : 'unknown'}>
                  {t !== undefined ? t : '?'}
                </td>
                <td className={s !== undefined ? 'computed' : 'unknown'}>
                  {s !== undefined ? s : '?'}
                </td>
                <td className={maxVal !== undefined ? 'computed' : 'unknown'}>
                  {maxVal !== undefined ? maxVal : '?'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
  