export default function TracePanel({ trace, currentStep, onStepChange }) {
  const maxStep = trace.length - 1;
  const cur = trace[currentStep] || {};
  const phase = cur.phase;

  const phaseLabel = phase === 'init' ? '初始化' :
    phase === 'lower' ? '下凸壳构建' :
    phase === 'upper-start' ? '切换阶段' :
    phase === 'upper' ? '上凸壳构建' :
    phase === 'done' ? '完成' : '—';

  const phaseClass = phase === 'init' ? 'phase-init' :
    phase === 'lower' ? 'phase-lower' :
    phase === 'upper-start' ? 'phase-init' :
    phase === 'upper' ? 'phase-upper' :
    phase === 'done' ? 'phase-done' : '';

  return (
    <div className="trace-panel">
      <h3>📊 算法步骤跟踪 <span className={`trace-phase ${phaseClass}`}>{phaseLabel}</span></h3>
      <div className="trace-nav">
        <button onClick={() => onStepChange(Math.max(0, currentStep - 1))} disabled={currentStep === 0}>
          ◀ 上一步
        </button>
        <span className="step-info">
          步骤 {currentStep} / {maxStep}
        </span>
        <button onClick={() => onStepChange(Math.min(maxStep, currentStep + 1))} disabled={currentStep === maxStep}>
          下一步 ▶
        </button>
        <button onClick={() => onStepChange(0)} disabled={currentStep === 0}>
          ⟲ 复位
        </button>
        <button onClick={() => onStepChange(maxStep)} disabled={currentStep === maxStep}>
          跳至末尾 ⏭
        </button>
      </div>
      <div className="trace-detail">
        <p><strong>当前点:</strong> {cur.currentPoint ? `(${cur.currentPoint[0]}, ${cur.currentPoint[1]})` : '—'}</p>
        {(phase === 'lower' || phase === 'upper') && (
          <>
            <p><strong>操作前凸壳:</strong> {JSON.stringify(phase === 'lower' ? cur.lowerBefore : cur.upperBefore)}</p>
            <p><strong>cross 值:</strong> {cur.cross !== null ? (cur.cross > 0 ? <span style={{color:'#16a34a'}}>+{cur.cross} (左转)</span> : cur.cross < 0 ? <span style={{color:'#dc2626'}}>{cur.cross} (右转)</span> : <span style={{color:'#ca8a04'}}>0 (共线)</span>) : '—'}</p>
            <p><strong>操作:</strong> {cur.action}</p>
            <p><strong>操作后凸壳:</strong> {JSON.stringify(phase === 'lower' ? cur.lower : cur.upper)}</p>
          </>
        )}
        {(phase === 'init' || phase === 'upper-start') && (
          <p><strong>状态:</strong> {cur.action}</p>
        )}
        {phase === 'done' && cur.finalHull && (
          <p><strong>✅ 最终凸包顶点:</strong> {JSON.stringify(cur.finalHull)}</p>
        )}
      </div>
    </div>
  );
}