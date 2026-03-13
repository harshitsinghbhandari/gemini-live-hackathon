// pages/ActivityPage.jsx
import { ActionCard } from '../components/ActionCard.jsx';
import { SessionTimer } from '../components/SessionTimer.jsx';
import { CONFIG } from '../config.js';

export function ActivityPage({ actions, sessionSeconds, agentStatus, onStop }) {
    async function handleStop() {
        try {
            await fetch(`${CONFIG.HELPER_URL}/stop`, { method: 'POST', signal: AbortSignal.timeout(3000) });
        } catch {/* ignore */ }
        onStop();
    }

    const dotClass = agentStatus === 'executing' ? 'executing'
        : agentStatus === 'auth' ? 'auth'
            : 'listening';

    return (
        <div className="page">
            {/* Top bar */}
            <div className="top-bar">
                <div className="top-bar-logo">
                    <div className={`logo-dot ${dotClass}`} />
                    <span>Aegis</span>
                </div>
                <SessionTimer seconds={sessionSeconds} />
            </div>

            {/* Action list */}
            <div className="action-list">
                {actions.length === 0 && (
                    <div style={{ color: 'var(--text-3)', fontSize: 13, textAlign: 'center', marginTop: 32 }}>
                        Waiting for actions…
                    </div>
                )}
                {actions.map((action, i) => (
                    <ActionCard
                        key={action.id || i}
                        action={action}
                        dim={i >= 3}
                    />
                ))}
            </div>

            {/* Stop button */}
            <div className="bottom-bar">
                <button className="btn btn-stop btn-full" onClick={handleStop}>
                    ■ &nbsp;Stop
                </button>
            </div>
        </div>
    );
}
