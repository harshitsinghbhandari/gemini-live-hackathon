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
                const t = new URLSearchParams({ device: CONFIG.DEVICE_ID });
                const res = await fetch(`${CONFIG.BACKEND_URL}/auth/pending?${t.toString()}`, {
                    signal: AbortSignal.timeout(2500)
                });
                if (res.ok) {
                    const data = await res.json();
                    console.log('Polling response:', data);
                    console.log('Has pending:', !!data.request_id);

                    if (data.request_id) {
                        setPendingReq(data);
                    } else {
                        setPendingReq(null);
                    }
                }
            } catch (err) {
                console.error('Polling error:', err);
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
