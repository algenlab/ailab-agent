import { useRef, useEffect } from 'react';

export default function Canvas({ points, trace, currentStep, width = 420, height = 400, margin = 45 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    if (points.length === 0) return;

    // Compute bounding box
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    points.forEach(([x, y]) => {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    });
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const scale = Math.min((width - 2 * margin) / rangeX, (height - 2 * margin) / rangeY);
    const offsetX = (width - rangeX * scale) / 2 - minX * scale;
    const offsetY = (height - rangeY * scale) / 2 - minY * scale;

    function tx(x) { return x * scale + offsetX; }
    function ty(y) { return height - (y * scale + offsetY); }

    // Draw grid (light)
    ctx.strokeStyle = '#e8e8e8';
    ctx.lineWidth = 0.5;
    for (let i = Math.floor(minX); i <= Math.ceil(maxX) + 1; i++) {
      const x = tx(i);
      ctx.beginPath();
      ctx.moveTo(x, margin - 5);
      ctx.lineTo(x, height - margin + 5);
      ctx.stroke();
    }
    for (let i = Math.floor(minY); i <= Math.ceil(maxY) + 1; i++) {
      const y = ty(i);
      ctx.beginPath();
      ctx.moveTo(margin - 5, y);
      ctx.lineTo(width - margin + 5, y);
      ctx.stroke();
    }
    // Axes
    ctx.strokeStyle = '#bbb';
    ctx.lineWidth = 1.2;
    const ox = tx(0), oy = ty(0);
    ctx.beginPath(); ctx.moveTo(ox, margin - 8); ctx.lineTo(ox, height - margin + 8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(margin - 8, oy); ctx.lineTo(width - margin + 8, oy); ctx.stroke();
    // Axis labels
    ctx.fillStyle = '#777';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    for (let v = Math.floor(minX); v <= Math.ceil(maxX); v++) {
      ctx.fillText(v, tx(v), oy + 14);
    }
    ctx.textAlign = 'left';
    for (let v = Math.floor(minY); v <= Math.ceil(maxY); v++) {
      ctx.fillText(v, ox - 16, ty(v) + 4);
    }

    // Draw all points
    points.forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(tx(x), ty(y), 5, 0, 2 * Math.PI);
      ctx.fillStyle = '#374151';
      ctx.fill();
      ctx.strokeStyle = '#1f2937';
      ctx.lineWidth = 1.8;
      ctx.stroke();
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`(${x},${y})`, tx(x), ty(y) - 12);
    });

    // Highlight current point
    const cur = trace[currentStep];
    if (cur && cur.currentPoint) {
      const [cx, cy] = cur.currentPoint;
      ctx.beginPath();
      ctx.arc(tx(cx), ty(cy), 9, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(255,165,0,0.6)';
      ctx.fill();
      ctx.strokeStyle = '#e67e00';
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }

    // Draw hull lines according to the current trace step
    for (let i = 0; i <= currentStep; i++) {
      const entry = trace[i];
      if (!entry) continue;
      if (entry.phase === 'lower' && entry.lower.length > 1) {
        drawPolyline(ctx, entry.lower, '#3b82f6', 2.5, tx, ty);
      }
      if (entry.phase === 'upper' && entry.upper.length > 1) {
        drawPolyline(ctx, entry.upper, '#ec4899', 2.5, tx, ty);
      }
      if (entry.phase === 'done' && entry.finalHull && entry.finalHull.length > 1) {
        drawPolygon(ctx, entry.finalHull, '#10b981', 3, tx, ty, true);
      }
    }
  }, [points, trace, currentStep, width, height, margin]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        border: '1.5px solid #d1d5db',
        borderRadius: '12px',
        background: '#fcfcfd',
        display: 'block',
        maxWidth: '100%',
      }}
    />
  );
}

function drawPolyline(ctx, pts, color, lineWidth, tx, ty) {
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const first = pts[0];
  ctx.moveTo(tx(first[0]), ty(first[1]));
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(tx(pts[i][0]), ty(pts[i][1]));
  }
  ctx.stroke();
}

function drawPolygon(ctx, pts, color, lineWidth, tx, ty, fill = false) {
  if (pts.length < 2) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const first = pts[0];
  ctx.moveTo(tx(first[0]), ty(first[1]));
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(tx(pts[i][0]), ty(pts[i][1]));
  }
  ctx.closePath();
  if (fill) {
    ctx.fillStyle = 'rgba(16,185,129,0.12)';
    ctx.fill();
  }
  ctx.stroke();
}