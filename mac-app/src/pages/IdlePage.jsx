// pages/IdlePage.jsx
import { useState, useEffect } from 'react';
import { CONFIG } from '../config.js';

export function IdlePage({ isConnected, onStart }) {
    const [helperReady, setHelperReady] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Poll helper health every 5 seconds
    useEffect(() => {
        let alive = true;
        async function checkHelper() {
            try {
                const r = await fetch(`${CONFIG.HELPER_URL}/health`, { signal: AbortSignal.timeout(1500) });
                if (alive) setHelperReady(r.ok);
            } catch {
                if (alive) setHelperReady(false);
            }
        }
        checkHelper();
        const interval = setInterval(checkHelper, 5000);
        return () => { alive = false; clearInterval(interval); };
    }, []);

    async function handleStart() {
        if (loading) return;
        if (!helperReady) {
            setError('Start helper server first:\npython aegis/helper_server.py');
            setTimeout(() => setError(''), 4000);
            return;
        }
        setLoading(true);
        setError('');
        try {
            const r = await fetch(`${CONFIG.HELPER_URL}/start`, {
                method: 'POST',
                signal: AbortSignal.timeout(3000),
            });
            const json = await r.json();
            if (json.started || json.reason === 'already running') {
                onStart();
            } else {
                setError('Failed to start agent');
                setTimeout(() => setError(''), 4000);
            }
        } catch {
            setError('Helper server unreachable');
            setTimeout(() => setError(''), 4000);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="page" style={{ position: 'relative' }}>
            {/* Title row */}
            <div
                style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    paddingTop: 52, paddingBottom: 12, gap: 10,
                }}
            >
                <span style={{ fontSize: 22, fontWeight: 300, letterSpacing: '0.1em', color: 'var(--text)' }}>
                    ◈ Aegis
                </span>
            </div>

            {/* Mic button area */}
            <div className="mic-wrapper">
                <div className="mic-btn-outer">
                    <button className="mic-btn" onClick={handleStart} disabled={loading} aria-label="Start Aegis">
                        <span className="mic-icon">{loading ? '⌛' : '🎙️'}</span>
                    </button>
                </div>
                <span className="idle-caption">
                    {loading ? 'Starting…' : 'Ready when you are.'}
                </span>
            </div>

            {/* Connection status */}
            <div className="divider" style={{ margin: '0 22px 0' }} />
            <div className="conn-row">
                <div className="conn-item">
                    <div className={`conn-dot ${isConnected ? 'ok' : 'error'}`} />
                    <span>ws: {isConnected ? 'connected' : 'disconnected'}</span>
                </div>
                <div className="conn-item">
                    <div className={`conn-dot ${helperReady ? 'ok' : 'error'}`} />
                    <span>helper: {helperReady ? 'ready' : 'offline'}</span>
                </div>
            </div>

            {/* Error toast */}
            {error && (
                <div className="error-toast" style={{ whiteSpace: 'pre-line' }}>{error}</div>
            )}
        </div>
    );
}
