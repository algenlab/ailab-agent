import React, { useMemo } from 'react';
import { flattenTrieForDisplay } from '../trieEngine';

export default function TrieVisualization({ stepData, currentStep, totalSteps }) {
  const { levels } = useMemo(() => {
    if (!stepData || !stepData.nodes) return { levels: [] };
    return flattenTrieForDisplay(stepData.nodes, stepData.activeNodePath);
  }, [stepData]);

  if (!levels.length) {
    return (
      <div className="card">
        <div className="card-header">🌳 Trie 结构可视化</div>
        <div style={{ textAlign: 'center', padding: 32, color: '#a0aec0' }}>
          正在构建可视化…
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">🌳 Trie 结构可视化</div>
      <div className="trie-viz">
        <div className="trie-canvas-wrap">
          <div className="trie-tree">
            {levels.map((level, levelIdx) => (
              <React.Fragment key={level.depth}>
                {levelIdx > 0 && (
                  <div className="trie-edge-row">
                    {level.nodes.map((node) => (
                      <div
                        key={`edge-${node.id}`}
                        className={`trie-edge-marker ${node.isActive ? 'active' : ''}`}
                      />
                    ))}
                  </div>
                )}
                <div className="trie-level">
                  {level.nodes.map((node) => {
                    let circleClass = 'trie-node-circle';
                    if (node.isRoot) circleClass += ' root-node';
                    if (node.isActive) {
                      if (stepData.phase === 'insert') circleClass += ' inserted';
                      else circleClass += ' highlight';
                    } else if (stepData.phase !== 'init') {
                      circleClass += ' faded';
                    }
                    return (
                      <div key={node.id} className="trie-node">
                        <div className={circleClass} title={`count=${node.count}`}>
                          <span className="node-char">
                            {node.isRoot ? '根' : (node.char || '?')}
                          </span>
                          <span className="node-count">{node.count}</span>
                        </div>
                        {!node.isRoot && node.path && (
                          <span className="trie-node-label">
                            {node.path.length > 4 ? '…' + node.path.slice(-3) : node.path}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
      <div
        className="step-description"
        dangerouslySetInnerHTML={{ __html: stepData.description }}
      />
      <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#a0aec0', textAlign: 'center' }}>
        步骤 {currentStep}/{totalSteps} — {stepData.phase === 'init' ? '初始化' : stepData.phase === 'insert' ? '插入阶段' : stepData.phase === 'query' ? '查询阶段' : '结果'}
      </div>
    </div>
  );
}
