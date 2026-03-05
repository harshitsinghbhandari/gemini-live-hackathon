// pages/MirrorPage.jsx
import React from 'react';
import { useAuditMirror } from '../hooks/useAuditMirror.js';
import { ActionCard } from '../components/ActionCard.jsx';
import { CONFIG } from '../config.js';

export function MirrorPage({ onStopSession }) {
    const logs = useAuditMirror();

    const handleStop = async () => {
        try {
            await fetch(`${CONFIG.BACKEND_URL}/session/stop`, { method: 'POST' });
            if (onStopSession) onStopSession();
        } catch (e) {
            console.error('Failed to stop session', e);
        }
    };

    return (
        <div className="page mirror-page">
            <div className="top-bar">
                <div className="top-bar-logo">
                    <span className="logo-icon">◈</span> Aegis
                </div>
                <div className="top-bar-subtitle">Mac session</div>
            </div>

            <div className="feed-container">
                {logs.length === 0 ? (
                    <div className="empty-state">No active session — open Aegis on your Mac</div>
                ) : (
                    logs.map((log) => (
                        <ActionCard key={log.id || log.timestamp} action={log} />
                    ))
                )}
            </div>

            <div className="bottom-bar">
                <button className="btn btn-stop btn-full" onClick={handleStop}>
                    ■ STOP SESSION
                </button>
            </div>
        </div>
    );
}
