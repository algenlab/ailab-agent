export function sortPoints(points) {
  return [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

function crossProduct(a, b, c) {
  // (b - a) × (c - b)
  return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
}

export function generateTrace(points) {
  const sorted = sortPoints(points);
  const trace = [];
  let lower = [];
  let stepNum = 0;

  trace.push({
    step: stepNum,
    phase: 'init',
    currentPoint: null,
    lower: lower.map(pt => [...pt]),
    upper: [],
    cross: null,
    action: '开始构建下凸壳。点按坐标排序。',
    description: '初始化',
  });

  // Lower hull construction
  for (const p of sorted) {
    stepNum++;
    const lowerBefore = lower.map(pt => [...pt]);
    let cross = null;
    let actionDesc = '';
    const pops = [];
    let lastCross = null;

    if (lower.length >= 2) {
      const a = lower[lower.length - 2];
      const b = lower[lower.length - 1];
      cross = crossProduct(a, b, p);
      lastCross = cross;
      while (lower.length >= 2 && crossProduct(lower[lower.length-2], lower[lower.length-1], p) <= 0) {
        const popped = lower.pop();
        pops.push(popped);
      }
      if (pops.length > 0) {
        actionDesc = `cross = ${lastCross} ≤ 0，回退并弹出 ${pops.map(pt => `(${pt[0]},${pt[1]})`).join('、')}`;
      } else {
        actionDesc = `cross = ${lastCross} > 0（左转），保留并添加点`;
      }
      cross = lastCross;
    } else {
      actionDesc = '凸壳点数不足 2，直接添加';
    }
    lower.push([...p]);
    trace.push({
      step: stepNum,
      phase: 'lower',
      currentPoint: [...p],
      lowerBefore: lowerBefore,
      lower: lower.map(pt => [...pt]),
      upper: [],
      cross: cross,
      action: actionDesc,
      description: `处理点 (${p[0]},${p[1]})`,
    });
  }

  // Switch to upper hull
  let upper = [];
  stepNum++;
  trace.push({
    step: stepNum,
    phase: 'upper-start',
    currentPoint: null,
    lower: lower.map(pt => [...pt]),
    upper: [],
    cross: null,
    action: '下凸壳构建完成。开始反向扫描构建上凸壳。',
    description: '切换至上凸壳',
  });

  // Upper hull construction (reverse order)
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    stepNum++;
    const upperBefore = upper.map(pt => [...pt]);
    let cross = null;
    let actionDesc = '';
    const pops = [];
    let lastCross = null;

    if (upper.length >= 2) {
      const a = upper[upper.length - 2];
      const b = upper[upper.length - 1];
      cross = crossProduct(a, b, p);
      lastCross = cross;
      while (upper.length >= 2 && crossProduct(upper[upper.length-2], upper[upper.length-1], p) <= 0) {
        const popped = upper.pop();
        pops.push(popped);
      }
      if (pops.length > 0) {
        actionDesc = `cross = ${lastCross} ≤ 0，回退并弹出 ${pops.map(pt => `(${pt[0]},${pt[1]})`).join('、')}`;
      } else {
        actionDesc = `cross = ${lastCross} > 0（左转），保留并添加点`;
      }
      cross = lastCross;
    } else {
      actionDesc = '凸壳点数不足 2，直接添加';
    }
    upper.push([...p]);
    trace.push({
      step: stepNum,
      phase: 'upper',
      currentPoint: [...p],
      lower: lower.map(pt => [...pt]),
      upper: upper.map(pt => [...pt]),
      upperBefore: upperBefore,
      cross: cross,
      action: actionDesc,
      description: `处理点 (${p[0]},${p[1]})`,
    });
  }

  // Final convex hull (counter‑clockwise): full lower + upper without first and last points
  const finalHull = [...lower, ...upper.slice(1, -1)];
  stepNum++;
  trace.push({
    step: stepNum,
    phase: 'done',
    currentPoint: null,
    lower: lower.map(pt => [...pt]),
    upper: upper.map(pt => [...pt]),
    finalHull: finalHull.map(pt => [...pt]),
    cross: null,
    action: `凸包构建完成。最终顶点（逆时针）: ${JSON.stringify(finalHull)}`,
    description: '完成',
  });

  return { trace, finalHull, sorted };
}

export function getCheckpointInfo(trace) {
  // Find the step where current point is [1,2] in lower phase
  for (const entry of trace) {
    if (
      entry.phase === 'lower' &&
      entry.currentPoint &&
      entry.currentPoint[0] === 1 &&
      entry.currentPoint[1] === 2
    ) {
      return {
        stepIndex: entry.step,
        lowerBefore: entry.lowerBefore,
        lowerAfter: entry.lower,
        cross: entry.cross,
      };
    }
  }
  return null;
}