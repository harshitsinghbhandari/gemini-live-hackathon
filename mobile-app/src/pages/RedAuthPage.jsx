// pages/RedAuthPage.jsx
import React, { useEffect } from 'react';
import { CountdownBar } from '../components/CountdownBar.jsx';
import FaceIDButton from '../components/FaceIDButton.jsx';
import { CONFIG } from '../config.js';

export function RedAuthPage({ request, onResolve }) {
    const { action, reason, created_at, request_id } = request;

    const handleApprove = () => {
        onResolve('approved');
    };

    const handleDeny = async () => {
        try {
            await fetch(`${CONFIG.BACKEND_URL}/auth/approve/${request_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved: false })
            });
        } catch (e) {
            console.error('Failed to send denial', e);
        }
        onResolve('denied');
    };

    const handleExpire = async () => {
        try {
            await fetch(`${CONFIG.BACKEND_URL}/auth/approve/${request_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approved: false })
            });
        } catch (e) {
            console.error('Failed to auto-deny', e);
        }
        onResolve('denied');
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
                timeoutSeconds={CONFIG.AUTH_TIMEOUT / 1000}
                onExpire={handleExpire}
            />

            <FaceIDButton
                requestId={request_id}
                onApprove={handleApprove}
                onDeny={() => onResolve('denied')}
            />

            <button className="btn btn-deny btn-full" onClick={handleDeny} style={{ marginTop: 8 }}>
                ✕ Deny
            </button>
        </div>
    );
}
