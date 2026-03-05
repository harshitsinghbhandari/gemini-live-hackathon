// components/ActionCard.jsx
import { useState } from 'react';
import { TierBadge } from './TierBadge.jsx';
import { formatDuration, formatTimestamp, toolkitLabel } from '../utils/formatters.js';

export function ActionCard({ action, dim = false }) {
    const [expanded, setExpanded] = useState(false);

    const tierClass = (action.tier || 'GREEN').toLowerCase();
    const isBlocked = action.blocked;
    const isSuccess = action.success;

    let statusIcon = '✓';
    if (isBlocked) statusIcon = '🚫';
    else if (!isSuccess && action.executed === false) statusIcon = '⏳';
    else if (!isSuccess) statusIcon = '✗';
    if (action.auth_used) statusIcon = '🔐';

    return (
        <div
            className={`action-card ${tierClass}${dim ? ' dim' : ''}${expanded ? ' expanded' : ''}`}
            onClick={() => setExpanded((e) => !e)}
        >
            <div className="card-main">
                <span className="card-action-text">{action.action || action.speak || '—'}</span>
                <span className="card-status-icon">{statusIcon}</span>
            </div>
            <div className="card-meta">
                <TierBadge tier={action.tier} />
                {action.tool && (
                    <span className="card-meta-text">{toolkitLabel(action.toolkit || action.tool)}</span>
                )}
                {action.duration_ms != null && (
                    <span className="card-meta-text">{formatDuration(action.duration_ms)}</span>
                )}
                {action.timestamp && (
                    <span className="card-meta-text" style={{ marginLeft: 'auto' }}>
                        {formatTimestamp(action.timestamp)}
                    </span>
                )}
            </div>
            {expanded && (
                <div className="card-expand">
                    {action.reason && <div><strong>Reason:</strong> {action.reason}</div>}
                    {action.speak && <div><strong>Info:</strong> {action.speak}</div>}
                    {action.error && <div style={{ color: 'var(--red)', marginTop: 4 }}><strong>Error:</strong> {action.error}</div>}
                    {action.tool && (
                        <pre>{JSON.stringify({ tool: action.tool, args: action.arguments }, null, 2)}</pre>
                    )}
                </div>
            )}
        </div>
    );
}
