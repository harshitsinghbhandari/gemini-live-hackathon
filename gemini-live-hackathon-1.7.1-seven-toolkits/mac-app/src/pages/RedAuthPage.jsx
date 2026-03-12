// pages/RedAuthPage.jsx
// Full-screen blocking overlay shown during RED-tier authentication
// Polls backend /auth/status/{request_id} every 2s

import { useEffect, useRef, useState } from 'react';
import { CountdownBar } from '../components/CountdownBar.jsx';
import { CONFIG } from '../config.js';

const AUTH_TIMEOUT = 30; // seconds

export function RedAuthPage({ pending, onApproved, onDenied }) {
    const [elapsed, setElapsed] = useState(0);
    const [flash, setFlash] = useState(''); // '' | 'approve' | 'deny'
    const donRef = useRef(false);

    // Tick elapsed seconds
    useEffect(() => {
        const id = setInterval(() => {
            setElapsed((e) => {
                if (e + 1 >= AUTH_TIMEOUT) {
                    clearInterval(id);
                    if (!donRef.current) { donRef.current = true; onDenied(true); }
                }
                return e + 1;
            });
        }, 1000);
        return () => clearInterval(id);
    }, [onDenied]);

    // Poll backend /auth/status/{request_id} every 2s
    useEffect(() => {
        if (!pending?.request_id) return;
        let alive = true;
        async function poll() {
            try {
                const r = await fetch(
                    `${CONFIG.BACKEND_URL}/auth/status/${pending.request_id}`,
                    { signal: AbortSignal.timeout(3000) }
                );
                if (!alive) return;
                if (r.ok) {
                    const data = await r.json();
                    if (data.status === 'approved' && !donRef.current) {
                        donRef.current = true;
                        setFlash('approve');
                        setTimeout(onApproved, 600);
                    } else if (data.status === 'denied' && !donRef.current) {
                        donRef.current = true;
                        setFlash('deny');
                        setTimeout(() => onDenied(false), 600);
                    }
                }
            } catch {/* network errors — keep polling */ }
        }
        const id = setInterval(poll, 2000);
        poll(); // immediate first poll
        return () => { alive = false; clearInterval(id); };
    }, [pending, onApproved, onDenied]);

    // Also react to WebSocket red_auth_result (surfaced via pending._result)
    useEffect(() => {
        if (pending?._result != null && !donRef.current) {
            donRef.current = true;
            if (pending._result) {
                setFlash('approve');
                setTimeout(onApproved, 600);
            } else {
                setFlash('deny');
                setTimeout(() => onDenied(false), 600);
            }
        }
    }, [pending, onApproved, onDenied]);

    return (
        <div
            className={`red-overlay${flash === 'approve' ? ' red-flash-approve' : flash === 'deny' ? ' red-flash-deny' : ''}`}
        >
            <div className="red-shield">🛡️</div>
            <div className="red-title">Requires your approval</div>

            {pending?.action && (
                <div className="red-action">{pending.action}</div>
            )}
            {pending?.reason && (
                <div style={{ fontSize: 12, color: 'var(--text-3)', textAlign: 'center' }}>
                    {pending.reason}
                </div>
            )}

            <CountdownBar total={AUTH_TIMEOUT} elapsed={elapsed} />

            <div className="red-hint">Check your iPhone →</div>
        </div>
    );
}
