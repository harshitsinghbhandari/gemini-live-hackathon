// hooks/useAuditMirror.js
import { useState, useEffect } from 'react';
import { CONFIG } from '../config.js';

export function useAuditMirror() {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        let mounted = true;

        // 1. Initial fetch
        async function fetchInitial() {
            try {
                const res = await fetch(`${CONFIG.BACKEND_URL}/audit/log?limit=20`, {
                    headers: { 'X-User-ID': CONFIG.USER_ID }
                });
                if (res.ok && mounted) {
                    const data = await res.json();
                    setLogs(data);
                }
            } catch (err) {
                console.error('Error fetching audit logs:', err);
            }
        }
        fetchInitial();

        // 2. SSE Stream
        const evtSource = new EventSource(`${CONFIG.BACKEND_URL}/audit/stream?user_id=${CONFIG.USER_ID}`);

        evtSource.onmessage = (event) => {
            if (!mounted) return;
            try {
                const newLog = JSON.parse(event.data);
                if (newLog) {
                    setLogs((prev) => {
                        // Deduplicate by ID
                        if (prev.some(l => l.id === newLog.id)) {
                            // Update existing
                            return prev.map(l => l.id === newLog.id ? newLog : l).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 20);
                        }
                        // Add new
                        return [newLog, ...prev].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 20);
                    });
                }
            } catch (err) {
                // Ignore parse errors
            }
        };

        return () => {
            mounted = false;
            evtSource.close();
        };
    }, []);

    return logs;
}
