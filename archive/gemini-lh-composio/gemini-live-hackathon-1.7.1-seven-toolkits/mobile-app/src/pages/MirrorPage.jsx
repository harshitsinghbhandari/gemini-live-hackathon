// pages/MirrorPage.jsx
import React, { useState, useEffect } from 'react';
import { useAuditMirror } from '../hooks/useAuditMirror.js';
import { ActionCard } from '../components/ActionCard.jsx';
import { CONFIG } from '../config.js';
import { registerFaceID } from '../components/FaceIDButton.jsx';

export function MirrorPage({ onStopSession }) {
    const logs = useAuditMirror();
    const [faceIDRegistered, setFaceIDRegistered] = useState(true); // Default to true to avoid flicker

    useEffect(() => {
        // Check if Face ID is registered
        fetch(`${CONFIG.BACKEND_URL}/webauthn/registered/${CONFIG.DEVICE_ID}`)
            .then(r => r.json())
            .then(data => setFaceIDRegistered(data.registered))
            .catch(() => { });
    }, []);

    const handleSetupFaceID = async () => {
        try {
            const success = await registerFaceID();
            if (success) {
                setFaceIDRegistered(true);
                alert("Face ID registered successfully!");
            }
        } catch (e) {
            console.error("Setup failed", e);
            alert(e)
            alert("Face ID setup failed. Make sure you are using HTTPS and standalone PWA mode.");
        }
    };

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
                {/* Show this if Face ID not yet registered */}
                {!faceIDRegistered && (
                    <div style={{
                        padding: "16px",
                        background: "#1e1e38",
                        borderRadius: "12px",
                        marginBottom: "16px",
                        border: "1px solid #7c3aed",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px"
                    }}>
                        <p style={{ color: "#a78bfa", margin: 0, fontSize: "14px", lineHeight: "1.4" }}>
                            ⚡ Setup Face ID to approve RED tier actions directly from your iPhone.
                        </p>
                        <button
                            onClick={handleSetupFaceID}
                            style={{
                                background: "#7c3aed",
                                color: "white",
                                border: "none",
                                borderRadius: "8px",
                                padding: "10px",
                                fontWeight: "600",
                                cursor: "pointer"
                            }}
                        >
                            Setup Now
                        </button>
                    </div>
                )}

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
