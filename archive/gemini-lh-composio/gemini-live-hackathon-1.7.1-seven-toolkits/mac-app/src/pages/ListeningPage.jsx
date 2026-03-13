// pages/ListeningPage.jsx
import { WaveformBar } from '../components/WaveformBar.jsx';
import { SessionTimer } from '../components/SessionTimer.jsx';
import { CONFIG } from '../config.js';

export function ListeningPage({ waveform, sessionSeconds, onStop, agentStatus }) {
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

            {/* Spacer */}
            <div style={{ flex: 1 }} />

            {/* Waveform visualizer */}
            <WaveformBar values={waveform} />
            <div className="listening-caption">
                {agentStatus === 'executing' ? 'Executing action…'
                    : agentStatus === 'auth' ? 'Waiting for auth…'
                        : 'I\'m hearing you'}
            </div>

            {/* Spacer */}
            <div style={{ flex: 1 }} />

            {/* Stop button */}
            <div className="bottom-bar">
                <button className="btn btn-stop btn-full" onClick={handleStop}>
                    ■ &nbsp;Stop
                </button>
            </div>
        </div>
    );
}
