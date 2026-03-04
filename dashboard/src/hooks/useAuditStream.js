import { useState, useEffect, useRef } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

export const useAuditStream = (onNewEntry) => {
  const [status, setStatus] = useState('OFFLINE');
  const eventSourceRef = useRef(null);

  useEffect(() => {
    const connect = () => {
      const eventSource = new EventSource(`${BACKEND_URL}/audit/stream`);

      eventSource.onopen = () => {
        setStatus('LIVE');
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onNewEntry(data);
        } catch (err) {
          console.error("Failed to parse SSE data:", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE error:", err);
        setStatus('OFFLINE');
        eventSource.close();
        setTimeout(connect, 3000);
      };

      eventSourceRef.current = eventSource;
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [onNewEntry]);

  return { status };
};
