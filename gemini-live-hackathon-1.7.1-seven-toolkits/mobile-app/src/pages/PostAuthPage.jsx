// pages/PostAuthPage.jsx
import React, { useEffect, useState } from 'react';

export function PostAuthPage({ result, onDismiss }) {
    const [scale, setScale] = useState(0);

    useEffect(() => {
        // Spring ease in CSS
        const timer = setTimeout(() => setScale(1), 50);
        const dismissTimer = setTimeout(() => onDismiss(), 2000); // 2 second auto-dismiss

        return () => {
            clearTimeout(timer);
            clearTimeout(dismissTimer);
        };
    }, [onDismiss]);

    const isApproved = result === 'approved';
    const iconClass = isApproved ? 'approve' : 'deny';
    const label = isApproved ? 'Approved' : 'Denied';

    return (
        <div className="page post-auth-page">
            <div
                className={`post-auth-icon ${iconClass}`}
                style={{ transform: `scale(${scale})`, transition: 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)' }}
            >
                {isApproved ? '✓' : '✕'}
            </div>
            <div className={`post-auth-text ${iconClass}`}>
                {label}
            </div>
        </div>
    );
}
