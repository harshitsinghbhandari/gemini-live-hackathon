// components/CountdownBar.jsx
import React, { useEffect, useState } from 'react';

export function CountdownBar({ createdAt, timeoutSeconds = 30, onExpire }) {
    const [secondsLeft, setSecondsLeft] = useState(timeoutSeconds);

    useEffect(() => {
        if (!createdAt) return;

        // createdAt can be ISO string or just rely on local timer
        // For simplicity, we just count down from when the component mounts if close enough,
        // or calculate absolute time. The prompt says "synced with created_at".
        const startMs = createdAt.toDate ? createdAt.toDate().getTime() : new Date(createdAt).getTime();

        const interval = setInterval(() => {
            const now = Date.now();
            const elapsed = Math.floor((now - startMs) / 1000);
            const remaining = timeoutSeconds - elapsed;

            if (remaining <= 0) {
                setSecondsLeft(0);
                clearInterval(interval);
                if (onExpire) onExpire();
            } else {
                setSecondsLeft(remaining);
            }
        }, 500);

        return () => clearInterval(interval);
    }, [createdAt, timeoutSeconds, onExpire]);

    const progressPct = Math.max(0, Math.min(100, (secondsLeft / timeoutSeconds) * 100));

    return (
        <div className="countdown-wrapper">
            <div className="countdown-track">
                <div className="countdown-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="countdown-label">{secondsLeft}s</div>
        </div>
    );
}
