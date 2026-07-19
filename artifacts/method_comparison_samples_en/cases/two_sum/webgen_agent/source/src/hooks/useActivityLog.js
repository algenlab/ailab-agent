import { useState, useCallback, useRef } from 'react';

let nextId = 1;

export function useActivityLog() {
  const [logEntries, setLogEntries] = useState([]);

  const addEntry = useCallback((entry) => {
    const newEntry = {
      id: nextId++,
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      ...entry
    };
    setLogEntries(prev => [...prev, newEntry]);
  }, []);

  return { logEntries, addEntry };
}