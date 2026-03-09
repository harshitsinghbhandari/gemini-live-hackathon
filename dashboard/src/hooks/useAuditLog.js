import { useState, useEffect } from 'react';
import { getBackendUrl } from '../utils/config';

const BACKEND_URL = getBackendUrl();

export const useAuditLog = () => {
  const [initialLogs, setInitialLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/audit/log?limit=50`, {
          headers: {
            'X-User-ID': localStorage.getItem('aegis_user_id') || ''
          }
        });
        if (!response.ok) {
          throw new Error(`Error: ${response.status}`);
        }
        const data = await response.json();
        setInitialLogs(data);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch initial audit logs:", err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  return { initialLogs, loading, error };
};
