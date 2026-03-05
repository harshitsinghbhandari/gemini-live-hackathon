// pages/RedAuthPage.jsx
import React, { useEffect } from 'react';
import { CountdownBar } from '../components/CountdownBar.jsx';
import { FaceIDButton } from '../components/FaceIDButton.jsx';
import { CONFIG } from '../config.js';

export function RedAuthPage({ request, onResolve }) {
    const { action, reason, created_at, id } = request;

    // Cleanup effect: auto-deny if component unmounts without resolving?
    // Let's rely on CountdownBar calling expire or explicit buttons.

    const handleApprove = async () => {
        await sendApproval(true);
        onResolve('approved');
    };

    const handleDeny = async () => {
        await sendApproval(false);
        onResolve('denied');
    };

    const handleExpire = async () => {
        // If the countdown bar reaches zero, the backend naturally times out after 30s.
        // We can also actively deny to be sure, or just resolve locally.
        await sendApproval(false);
        onResolve('denied');
    };

    const sendApproval = async (approved) => {
        try {
            if (!id) return;
            await fetch(`${CONFIG.BACKEND_URL}/auth/approve/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved })
            });
        } catch (e) {
            console.error('Failed to send approval', e);
        }
    };

    return (
        <div className="page auth-page">
            <div className="auth-shield">🛡️</div>
            <div className="auth-label">Aegis wants to:</div>

            <div className="auth-card">
                <div className="auth-action-text">{action}</div>
            </div>

            <div className="auth-reason-label">Because:</div>
            <div className="auth-reason-text">{reason}</div>

            <CountdownBar
                createdAt={created_at}
                timeoutSeconds={CONFIG.AUTH_TIMEOUT}
                onExpire={handleExpire}
            />

            <FaceIDButton onApprove={handleApprove} />

            <button className="btn btn-deny btn-full" onClick={handleDeny} style={{ marginTop: 8 }}>
                ✕ Deny
            </button>
        </div>
    );
}
