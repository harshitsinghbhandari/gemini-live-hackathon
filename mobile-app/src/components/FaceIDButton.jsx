// components/FaceIDButton.jsx
import React from 'react';
import { startAuthentication, startRegistration } from '@simplewebauthn/browser';
import { CONFIG } from '../config.js';

const USER_ID = CONFIG.DEVICE_ID; // "harshit-iphone"

export async function registerFaceID() {
    /** Call once to register Face ID on this device */
    const options = await fetch(`${CONFIG.BACKEND_URL}/webauthn/register/options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID })
    }).then(r => r.json());

    // This triggers the native iOS/Safari biometric prompt for registration
    const credential = await startRegistration(options);

    const verification = await fetch(`${CONFIG.BACKEND_URL}/webauthn/register/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID, credential })
    }).then(r => r.json());

    return verification.verified;
}

export async function authenticateWithFaceID(requestId) {
    /** Trigger Face ID and approve auth request */
    // Get auth challenge
    const options = await fetch(`${CONFIG.BACKEND_URL}/webauthn/auth/options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID })
    }).then(r => r.json());

    if (options.error === 'not_registered') {
        throw new Error('NEEDS_REGISTRATION');
    }

    // This triggers Face ID on iPhone automatically
    const credential = await startAuthentication(options);

    // Verify and approve
    const result = await fetch(`${CONFIG.BACKEND_URL}/webauthn/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: USER_ID,
            credential,
            request_id: requestId
        })
    }).then(r => r.json());

    return result.verified;
}

export function FaceIDButton({ requestId, onApprove, onDeny }) {
    const [loading, setLoading] = React.useState(false);
    const [needsSetup, setNeedsSetup] = React.useState(false);

    React.useEffect(() => {
        // Check if Face ID is registered
        fetch(`${CONFIG.BACKEND_URL}/webauthn/registered/${USER_ID}`)
            .then(r => r.json())
            .then(data => setNeedsSetup(!data.registered))
            .catch(() => { });
    }, []);

    const handleApprove = async () => {
        setLoading(true);
        try {
            if (needsSetup) {
                // Register first
                const registered = await registerFaceID();
                if (!registered) throw new Error('Registration failed');
                setNeedsSetup(false);
            }

            const verified = await authenticateWithFaceID(requestId);
            if (verified) {
                onApprove();
            } else {
                onDeny();
            }
        } catch (err) {
            if (err.message === 'NEEDS_REGISTRATION') {
                setNeedsSetup(true);
            }
            console.error('Face ID error:', err);
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleApprove}
            disabled={loading}
            style={{
                width: "100%",
                padding: "18px",
                background: loading ? "#4c1d95" : "#7c3aed",
                color: "white",
                border: "none",
                borderRadius: "12px",
                fontSize: "18px",
                fontWeight: "600",
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "10px",
                transition: "background 0.2s"
            }}
        >
            {loading ? "Verifying..." : needsSetup ? "Setup Face ID" : "Approve with Face ID 👤"}
        </button>
    );
}

export default FaceIDButton;
