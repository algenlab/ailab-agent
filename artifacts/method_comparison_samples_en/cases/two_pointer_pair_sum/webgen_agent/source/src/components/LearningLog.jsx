import React, { useRef, useEffect } from 'react';

export default function LearningLog({ entries }) {
  const logEndRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries]);

  const getEntryIcon = (type) => {
    switch (type) {
      case 'navigation': return '▶';
      case 'answer_correct': return '✓';
      case 'answer_incorrect': return '✗';
      case 'hint': return '💡';
      case 'show_answer': return '👁';
      case 'reset': return '↺';
      case 'session_start': return '●';
      default: return '•';
    }
  };

  const getEntryClass = (type) => {
    switch (type) {
      case 'answer_correct': return 'log-correct';
      case 'answer_incorrect': return 'log-incorrect';
      case 'hint': return 'log-hint';
      case 'show_answer': return 'log-show-answer';
      case 'reset': return 'log-reset';
      case 'navigation': return 'log-navigation';
      default: return 'log-default';
    }
  };

  return (
    <div className="learning-log" role="log" aria-label="Learning activity log" aria-live="polite">
      <h3 className="log-header">Learning Log</h3>
      <div className="log-entries">
        {entries.length === 0 && (
          <p className="log-empty">No activity yet. Start exploring the algorithm!</p>
        )}
        {entries.map((entry, index) => (
          <div key={entry.id || index} className={`log-entry ${getEntryClass(entry.type)}`}>
            <span
              className="log-icon"
              dangerouslySetInnerHTML={{ __html: getEntryIcon(entry.type) }}
              aria-hidden="true"
            />
            <span className="log-time">{entry.timestamp}</span>
            <span className="log-description">{entry.description}</span>
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}