import { useState, useCallback } from 'react';

export interface LogEntry {
  id: number;
  timestamp: Date;
  message: string;
  type: 'info' | 'correct' | 'incorrect' | 'hint' | 'answer' | 'navigation' | 'system';
}

let nextLogId = 1;

export function useActivityLog() {
  const [entries, setEntries] = useState<LogEntry[]>(() => [
    {
      id: 0,
      timestamp: new Date(),
      message: 'Session started. Welcome to the Number of Provinces interactive learning page.',
      type: 'system',
    },
  ]);

  const addEntry = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    setEntries((prev) => [
      ...prev,
      { id: nextLogId++, timestamp: new Date(), message, type },
    ]);
  }, []);

  const clearLog = useCallback(() => {
    setEntries([]);
    nextLogId = 1;
  }, []);

  return { entries, addEntry, clearLog };
}
