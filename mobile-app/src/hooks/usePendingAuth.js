// hooks/usePendingAuth.js
// Polls backend /auth/pending every 3 seconds to check if device has pending requests

import { useState, useEffect, useRef } from 'react';
import { CONFIG } from '../config.js';

export function usePendingAuth(isActive) {
    const [pendingReq, setPendingReq] = useState(null);
    const timerRef = useRef(null);

    useEffect(() => {
        // Stop polling if isActive is false (e.g. we are already showing the Auth screen)
        if (!isActive) {
            if (timerRef.current) clearInterval(timerRef.current);
            return;
        }

        async function poll() {
            try {
                // Querying auth requests that are pending. We can fetch audit log and filter or ask a specific endpoint.
                // The backend doesn't have an explicit `/auth/pending` in main.py, but it has `/audit/log`.
                // Alternatively, the prompt implies there is an endpoint or we can determine it from the audit stream.
                // Wait, the prompt says: "Polls GET {BACKEND_URL}/auth/pending every 3 seconds".
                // Although I didn't see `/auth/pending` in main.py, I will implement it as requested. It might be implied or assume it exists/will exist.
                // Let's implement the polling exactly as specified:
                const t = new URLSearchParams({ device: CONFIG.DEVICE_ID });
                const res = await fetch(`${CONFIG.BACKEND_URL}/auth/pending?${t.toString()}`, {
                    signal: AbortSignal.timeout(2500)
                });
                if (res.ok) {
                    const data = await res.json();
                    // Assume returns { request: {...} } or null
                    if (data.request) {
                        setPendingReq(data.request);
                    } else {
                        setPendingReq(null);
                    }
                }
            } catch (err) {
                // silent on network errors
            }
        }

        // poll right away, then every POLL_INTERVAL
        poll();
        timerRef.current = setInterval(poll, CONFIG.POLL_INTERVAL);

        return () => clearInterval(timerRef.current);
    }, [isActive]);

    const clearPending = () => setPendingReq(null);

    return { pendingReq, clearPending };
}
