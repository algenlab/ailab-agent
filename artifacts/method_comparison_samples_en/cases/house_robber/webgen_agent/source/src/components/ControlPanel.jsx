import React, { useState, useRef, useEffect, useCallback } from 'react';

export default function ControlPanel({ currentStep, maxStep, onPrev, onNext, onReset, onGoToStep }) {
  const [autoPlaying, setAutoPlaying] = useState(false);
  const intervalRef = useRef(null);

  const stopAutoPlay = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setAutoPlaying(false);
  }, []);

  const startAutoPlay = useCallback(() => {
    if (autoPlaying) return;
    setAutoPlaying(true);
    intervalRef.current = setInterval(() => {
      onNext();
    }, 1200);
  }, [autoPlaying, onNext]);

  const handleAutoPlay = () => {
    if (autoPlaying) {
      stopAutoPlay();
    } else {
      startAutoPlay();
    }
  };

  useEffect(() => {
    if (currentStep >= maxStep && autoPlaying) {
      stopAutoPlay();
    }
  }, [currentStep, maxStep, autoPlaying, stopAutoPlay]);

  useEffect(() => {
    return () => stopAutoPlay();
  }, [stopAutoPlay]);

  const isFirst = currentStep === 0;
  const isLast = currentStep === maxStep;

  return (
    <div className="control-panel">
      <div className="nav-buttons">
        <button 
          onClick={() => onGoToStep(0)} 
          disabled={isFirst} 
          className="nav-btn jump-start"
          aria-label="Jump to first step"
          title="Go to first step"
        >
          ⏮ First
        </button>
        <button 
          onClick={onPrev} 
          disabled={isFirst} 
          className="nav-btn prev-btn"
          aria-label="Go to previous step"
          title="Previous step"
        >
          ◀ Previous
        </button>
        <button 
          onClick={handleAutoPlay} 
          className={`nav-btn play-btn ${autoPlaying ? 'playing' : ''}`}
          aria-label={autoPlaying ? 'Pause auto-play' : 'Start auto-play'}
          title={autoPlaying ? 'Pause automatic playback' : 'Automatically step through the algorithm'}
        >
          {autoPlaying ? '⏸️ Pause' : '▶ Play'}
        </button>
        <button 
          onClick={onNext} 
          disabled={isLast} 
          className="nav-btn next-btn"
          aria-label="Go to next step"
          title="Next step"
        >
          Next ▶
        </button>
        <button 
          onClick={() => onGoToStep(maxStep)} 
          disabled={isLast} 
          className="nav-btn jump-end"
          aria-label="Jump to last step"
          title="Go to last step"
        >
          ⏭ Last
        </button>
      </div>
      <div className="reset-and-step">
        <button 
          onClick={onReset} 
          disabled={isFirst} 
          className="nav-btn reset-btn-control"
          aria-label="Reset to first step"
          title="Reset to step 0"
        >
          ↺ Reset
        </button>
        <div className="step-input">
          <label htmlFor="step-input">Go to step:</label>
          <input
            id="step-input"
            type="number"
            min={0}
            max={maxStep}
            value={currentStep}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val)) onGoToStep(val);
            }}
            aria-label="Go to step number"
            title="Jump to a specific step number"
          />
          <span className="step-range">of {maxStep} ({maxStep + 1} total)</span>
        </div>
      </div>
      <style>{`
        .control-panel {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin: 20px 0;
          padding: 16px 20px;
          background: #f1f5f9;
          border-radius: 12px;
          border: 1px solid #e2e8f0;
        }
        .nav-buttons {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .nav-btn {
          padding: 10px 18px;
          border: 2px solid transparent;
          border-radius: 8px;
          background: #ffffff;
          color: #1e293b;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 0.9rem;
          white-space: nowrap;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .nav-btn:disabled {
          background: #e2e8f0;
          color: #94a3b8;
          cursor: not-allowed;
          box-shadow: none;
        }
        .nav-btn:hover:not(:disabled) {
          background: #dbeafe;
          border-color: #3b82f6;
          transform: translateY(-1px);
          box-shadow: 0 2px 6px rgba(0,0,0,0.12);
        }
        .prev-btn, .next-btn {
          background: #1e293b;
          color: white;
        }
        .prev-btn:hover:not(:disabled), .next-btn:hover:not(:disabled) {
          background: #0f172a;
          border-color: #0f172a;
        }
        .play-btn {
          background: #2563eb;
          color: white;
        }
        .play-btn.playing {
          background: #f59e0b;
          color: #1e293b;
        }
        .play-btn:hover:not(:disabled) {
          background: #1d4ed8;
        }
        .play-btn.playing:hover:not(:disabled) {
          background: #d97706;
        }
        .jump-start, .jump-end {
          background: #e2e8f0;
          color: #334155;
          padding: 10px 14px;
        }
        .reset-and-step {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          padding-top: 8px;
          border-top: 1px solid #e2e8f0;
        }
        .reset-btn-control {
          background: #ef4444;
          color: white;
        }
        .reset-btn-control:hover:not(:disabled) {
          background: #dc2626;
          border-color: #dc2626;
        }
        .step-input {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-left: auto;
        }
        .step-input label {
          font-weight: 600;
          font-size: 0.9rem;
          color: #475569;
        }
        .step-input input {
          width: 60px;
          padding: 8px 10px;
          border-radius: 6px;
          border: 1px solid #cbd5e1;
          font-family: monospace;
          text-align: center;
          font-size: 0.95rem;
          outline: none;
          transition: border-color 0.2s;
        }
        .step-input input:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
        }
        .step-range {
          font-family: monospace;
          font-size: 0.85rem;
          color: #64748b;
          white-space: nowrap;
        }
        @media (max-width: 640px) {
          .control-panel {
            padding: 12px;
          }
          .nav-btn {
            padding: 8px 12px;
            font-size: 0.8rem;
          }
          .reset-and-step {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
          }
          .step-input {
            margin-left: 0;
          }
        }
      `}</style>
    </div>
  );
}