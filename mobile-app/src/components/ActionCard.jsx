// components/ActionCard.jsx
import React from 'react';
import { formatTimestamp, toolkitLabel } from '../utils/formatters.js';
import { TierBadge } from './TierBadge.jsx';

export function ActionCard({ action }) {
    const {
        tier,
        action: text,
        tool,
        toolkit,
        success,
        blocked,
        timestamp
    } = action;

    // Determine border color class
    let colorClass = 'green';
    if (tier === 'yellow') colorClass = 'yellow';
    if (tier === 'red') colorClass = 'red';

    // Status icon
    let statusIcon = '✓';
    if (blocked) statusIcon = '🔐';
    else if (!success && success !== undefined) statusIcon = '⚠️';

    const toolDisplay = tool ? tool : toolkitLabel(toolkit);

    return (
        <div className={`action-card ${colorClass}`}>
            <div className="card-main">
                <div className="card-action-text">{text}</div>
                <div className="card-status-icon">{statusIcon}</div>
            </div>
            <div className="card-meta">
                <TierBadge tier={tier} />
                <span className="card-meta-text">{toolDisplay}</span>
                <span className="card-meta-text" style={{ marginLeft: 'auto' }}>
                    {formatTimestamp(timestamp)}
                </span>
            </div>
        </div>
    );
}
