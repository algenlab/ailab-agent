import { useState, useCallback } from 'react';

function formatTime() {
  const d = new Date();
  return d.toLocaleTimeString('zh-CN', { hour12: false });
}

export function useActivityLog() {
  const [entries, setEntries] = useState([]);

  const log = useCallback((type, message) => {
    setEntries(prev => [...prev, { type, message, time: formatTime() }]);
  }, []);

  return { entries, log };
}
