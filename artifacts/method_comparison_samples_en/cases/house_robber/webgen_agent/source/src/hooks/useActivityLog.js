import { useState, useCallback } from 'react';

export function useActivityLog() {
  const [log, setLog] = useState([]);

  const addLog = useCallback((message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLog(prev => [...prev, { timestamp, message }]);
  }, []);

  return { log, addLog };
}