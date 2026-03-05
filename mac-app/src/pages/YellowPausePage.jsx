// pages/YellowPausePage.jsx
// Renders on top of the ActivityPage — semi-transparent overlay

import { ActionCard } from '../components/ActionCard.jsx';
import { SessionTimer } from '../components/SessionTimer.jsx';

export function YellowPausePage({ pending, actions, sessionSeconds, sendMessage, onResolve }) {
    function respond(confirmed) {
        if (!pending) return;
        sendMessage({
            event: 'yellow_response',
            data: { id: pending.id, confirmed },
        });
        onResolve();
    }

    return (
        <div className="page" style={{ position: 'relative' }}>
            {/* Dimmed activity underneath */}
            <div className="top-bar" style={{ opacity: 0.25 }}>
                <div className="top-bar-logo">
                    <div className="logo-dot" style={{ background: 'var(--amber)' }} />
                    <span>Aegis</span>
                </div>
                <SessionTimer seconds={sessionSeconds} />
            </div>
            <div className="action-list" style={{ opacity: 0.2, pointerEvents: 'none', flex: 1 }}>
                {actions.slice(0, 5).map((a, i) => (
                    <ActionCard key={a.id || i} action={a} dim />
                ))}
            </div>

            {/* Overlay */}
            <div className="yellow-overlay">
                <div className="yellow-dim-bg" />
                <div className="yellow-modal">
                    <div className="yellow-modal-icon">💬</div>
                    <div className="yellow-modal-title">Confirmation Needed</div>
                    <div className="yellow-modal-text">
                        {pending?.question || pending?.speak || 'Shall I proceed with this action?'}
                    </div>
                    {pending?.action && pending.action !== pending?.speak && (
                        <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 16, fontStyle: 'italic' }}>
                            {pending.action}
                        </div>
                    )}
                    <div className="yellow-actions">
                        <button className="btn btn-amber" onClick={() => respond(true)}>
                            Proceed
                        </button>
                        <button className="btn btn-ghost" onClick={() => respond(false)}>
                            Skip
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
