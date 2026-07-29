import React, { useRef, useEffect, useCallback } from 'react';

// Data coordinate bounds for the visualization
const DATA_MIN_X = -0.6;
const DATA_MAX_X = 2.6;
const DATA_MIN_Y = -0.6;
const DATA_MAX_Y = 2.6;
const PADDING = 50;

function toCanvasX(dataX, canvasW) {
  return PADDING + ((dataX - DATA_MIN_X) / (DATA_MAX_X - DATA_MIN_X)) * (canvasW - 2 * PADDING);
}

function toCanvasY(dataY, canvasH) {
  return canvasH - PADDING - ((dataY - DATA_MIN_Y) / (DATA_MAX_Y - DATA_MIN_Y)) * (canvasH - 2 * PADDING);
}

function drawGrid(ctx, w, h) {
  ctx.strokeStyle = '#e8ecf1';
  ctx.lineWidth = 0.5;
  ctx.setLineDash([4, 4]);
  for (let x = 0; x <= 2; x += 0.5) {
    const cx = toCanvasX(x, w);
    ctx.beginPath();
    ctx.moveTo(cx, PADDING);
    ctx.lineTo(cx, h - PADDING);
    ctx.stroke();
  }
  for (let y = 0; y <= 2; y += 0.5) {
    const cy = toCanvasY(y, h);
    ctx.beginPath();
    ctx.moveTo(PADDING, cy);
    ctx.lineTo(w - PADDING, cy);
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

function drawAxes(ctx, w, h) {
  const ox = toCanvasX(0, w);
  const oy = toCanvasY(0, h);

  // Draw axis lines
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(PADDING, oy);
  ctx.lineTo(w - PADDING, oy);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(ox, PADDING);
  ctx.lineTo(ox, h - PADDING);
  ctx.stroke();

  // Draw arrowheads on both axes
  const arrowSize = 7;

  // X-axis arrowhead
  const xTip = w - PADDING;
  ctx.fillStyle = '#94a3b8';
  ctx.beginPath();
  ctx.moveTo(xTip, oy);
  ctx.lineTo(xTip - arrowSize, oy - arrowSize / 2);
  ctx.lineTo(xTip - arrowSize, oy + arrowSize / 2);
  ctx.closePath();
  ctx.fill();

  // Y-axis arrowhead
  const yTip = PADDING;
  ctx.beginPath();
  ctx.moveTo(ox, yTip);
  ctx.lineTo(ox - arrowSize / 2, yTip + arrowSize);
  ctx.lineTo(ox + arrowSize / 2, yTip + arrowSize);
  ctx.closePath();
  ctx.fill();

  // X-axis tick labels — positioned below the axis
  ctx.fillStyle = '#64748b';
  ctx.font = '600 12px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let v = 1; v <= 2; v++) {
    const cx = toCanvasX(v, w);
    ctx.fillText(String(v), cx, toCanvasY(0, h) + 18);
  }
  // X-axis "0" label — offset to the right of the Y axis to avoid overlap
  ctx.fillText('0', toCanvasX(0, w) + 13, toCanvasY(0, h) + 18);

  // Y-axis tick labels — positioned to the left of the axis
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let v = 1; v <= 2; v++) {
    const cy = toCanvasY(v, h);
    ctx.fillText(String(v), toCanvasX(0, w) - 16, cy);
  }
  // Y-axis "0" label — offset above the X axis to avoid overlap
  ctx.fillText('0', toCanvasX(0, w) - 16, toCanvasY(0, h) - 6);

  // Axis names with consistent positioning
  ctx.fillStyle = '#475569';
  ctx.font = 'italic bold 13px -apple-system, BlinkMacSystemFont, sans-serif';
  // X-axis label
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText('x', w - PADDING + 14, toCanvasY(0, h) + 18);
  // Y-axis label
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  ctx.fillText('y', toCanvasX(0, w), PADDING - 14);
}

function drawPoint(ctx, x, y, label, color, radius, w, h) {
  const cx = toCanvasX(x, w);
  const cy = toCanvasY(y, h);

  // Glow for highlighted points
  if (radius > 8) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius + 6, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
    ctx.fill();
  }

  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Label slightly offset
  ctx.fillStyle = '#1e293b';
  ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(label, cx + radius + 4, cy - radius - 2);
}

function drawLine(ctx, fromX, fromY, toX, toY, color, width, w, h) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(toCanvasX(fromX, w), toCanvasY(fromY, h));
  ctx.lineTo(toCanvasX(toX, w), toCanvasY(toY, h));
  ctx.stroke();
}

function drawPolygon(ctx, points, fillColor, strokeColor, lineWidth, w, h) {
  if (points.length < 2) return;
  ctx.beginPath();
  const first = points[0];
  ctx.moveTo(toCanvasX(first[0], w), toCanvasY(first[1], h));
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(toCanvasX(points[i][0], w), toCanvasY(points[i][1], h));
  }
  ctx.closePath();
  if (fillColor) {
    ctx.fillStyle = fillColor;
    ctx.fill();
  }
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.stroke();
}

function drawCrossArc(ctx, o, a, b, crossValue, w, h) {
  const ox = toCanvasX(o[0], w);
  const oy = toCanvasY(o[1], h);
  const ax = toCanvasX(a[0], w);
  const ay = toCanvasY(a[1], h);
  const bx = toCanvasX(b[0], w);
  const by = toCanvasY(b[1], h);

  // Vectors
  const v1x = ax - ox;
  const v1y = ay - oy;
  const v2x = bx - ox;
  const v2y = by - oy;

  const angle1 = Math.atan2(v1y, v1x);
  const angle2 = Math.atan2(v2y, v2x);

  const radius = 30;
  const arcColor = crossValue > 0 ? '#10b981' : '#ef4444';

  ctx.beginPath();
  ctx.arc(ox, oy, radius, angle1, angle2, crossValue <= 0);
  ctx.strokeStyle = arcColor;
  ctx.lineWidth = 2.5;
  ctx.setLineDash([]);
  ctx.stroke();

  // Arrowhead at the end
  const endAngle = angle2;
  const arrowX = ox + radius * Math.cos(endAngle);
  const arrowY = oy + radius * Math.sin(endAngle);
  const arrowSize = 7;
  const arrowAngle1 = endAngle + Math.PI / 6;
  const arrowAngle2 = endAngle - Math.PI / 6;

  ctx.fillStyle = arcColor;
  ctx.beginPath();
  ctx.moveTo(arrowX, arrowY);
  ctx.lineTo(
    arrowX - arrowSize * Math.cos(arrowAngle1),
    arrowY - arrowSize * Math.sin(arrowAngle1)
  );
  ctx.lineTo(
    arrowX - arrowSize * Math.cos(arrowAngle2),
    arrowY - arrowSize * Math.sin(arrowAngle2)
  );
  ctx.closePath();
  ctx.fill();

  // Cross value label
  const midAngle = (angle1 + angle2) / 2;
  const labelR = radius + 20;
  ctx.fillStyle = arcColor;
  ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(
    `${crossValue > 0 ? '+' : ''}${crossValue}`,
    ox + labelR * Math.cos(midAngle),
    oy + labelR * Math.sin(midAngle) + 4
  );
}

export default function CanvasView({ trace, inputPoints, sortedPoints, expectedOutput }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = '#fafbfd';
    ctx.fillRect(0, 0, w, h);

    drawGrid(ctx, w, h);
    drawAxes(ctx, w, h);

    const displayPoints = sortedPoints || inputPoints;
    const lowerHull = trace.lowerHull || [];
    const upperHull = trace.upperHull || [];
    const finalHull = trace.finalHull;
    const currentIdx = trace.currentPointIdx;

    // Draw lower hull edges
    if (lowerHull.length >= 2) {
      for (let i = 0; i < lowerHull.length - 1; i++) {
        drawLine(ctx, lowerHull[i][0], lowerHull[i][1], lowerHull[i + 1][0], lowerHull[i + 1][1], '#3b82f6', 3, w, h);
      }
    }

    // Draw upper hull edges (dashed during construction, solid when done)
    if (upperHull.length >= 2) {
      const upperDone = trace.phase === 'upper-done' || trace.phase === 'combine' || trace.phase === 'done';
      if (!upperDone) {
        ctx.setLineDash([6, 4]);
      }
      for (let i = 0; i < upperHull.length - 1; i++) {
        drawLine(ctx, upperHull[i][0], upperHull[i][1], upperHull[i + 1][0], upperHull[i + 1][1], '#f59e0b', 3, w, h);
      }
      ctx.setLineDash([]);
    }

    // Draw final hull polygon
    if (finalHull && finalHull.length >= 3) {
      drawPolygon(ctx, finalHull, 'rgba(16, 185, 129, 0.12)', '#10b981', 3.5, w, h);
    }

    // Draw cross product arc if available
    if (trace.crossInfo) {
      drawCrossArc(ctx, trace.crossInfo.o, trace.crossInfo.a, trace.crossInfo.b, trace.crossInfo.value, w, h);
    }

    // Determine which points to dim (popped points)
    const poppedSet = new Set((trace.poppedIndices || []).map((i) => `${displayPoints[i][0]},${displayPoints[i][1]}`));

    // Draw all display points
    displayPoints.forEach((pt, idx) => {
      const key = `${pt[0]},${pt[1]}`;
      const isCurrent = idx === currentIdx;
      const isPopped = poppedSet.has(key);
      const isInLowerHull = lowerHull.some((h) => h[0] === pt[0] && h[1] === pt[1]);
      const isInUpperHull = upperHull.some((h) => h[0] === pt[0] && h[1] === pt[1]);

      let color = '#94a3b8';
      let radius = 7;
      if (isPopped && trace.phase === 'lower') {
        color = '#fca5a5';
        radius = 6;
      } else if (isInLowerHull) {
        color = '#3b82f6';
        radius = 8;
      } else if (isInUpperHull) {
        color = '#f59e0b';
        radius = 8;
      }
      if (isCurrent) {
        color = '#ef4444';
        radius = 11;
      }

      const label = `(${pt[0]},${pt[1]})`;
      drawPoint(ctx, pt[0], pt[1], label, color, radius, w, h);
    });
  }, [trace, inputPoints, sortedPoints, expectedOutput]);

  useEffect(() => {
    draw();
    const handleResize = () => draw();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  return (
    <div className="canvas-container" ref={containerRef}>
      <canvas ref={canvasRef} />
    </div>
  );
}