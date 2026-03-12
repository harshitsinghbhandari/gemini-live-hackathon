// src/App.jsx
// Central state machine: IDLE → LISTENING → ACTIVITY
//               ACTIVITY ↔ YELLOW_PAUSE
//               ACTIVITY ↔ RED_AUTH

import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket.js';
import { useSessionTimer } from './hooks/useSessionTimer.js';

import { IdlePage } from './pages/IdlePage.jsx';
import { ListeningPage } from './pages/ListeningPage.jsx';
import { ActivityPage } from './pages/ActivityPage.jsx';
import { YellowPausePage } from './pages/YellowPausePage.jsx';
import { RedAuthPage } from './pages/RedAuthPage.jsx';

const STATES = {
    IDLE: 'IDLE',
    LISTENING: 'LISTENING',
    ACTIVITY: 'ACTIVITY',
    YELLOW_PAUSE: 'YELLOW_PAUSE',
    RED_AUTH: 'RED_AUTH',
};

export default function App() {
    const [appState, setAppState] = useState(STATES.IDLE);
    const [prevState, setPrevState] = useState(STATES.ACTIVITY); // state to return to after overlays

    const {
        isConnected,
        status,
        actions,
        pendingYellow,
        pendingRed,
        waveform,
        sendMessage,
        clearPendingYellow,
        clearPendingRed,
    } = useWebSocket();

    const sessionRunning = appState !== STATES.IDLE;
    const sessionSeconds = useSessionTimer(sessionRunning);

    // Register service worker for PWA
    useEffect(() => {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(() => { });
        }
    }, []);

    // WebSocket drives state transitions ─────────────────────────────────
    useEffect(() => {
        if (status === 'idle') {
            setAppState(STATES.IDLE);
        } else if (status === 'listening' && appState === STATES.IDLE) {
            setAppState(STATES.LISTENING);
        }
    }, [status]);

    // First action → move from LISTENING → ACTIVITY
    useEffect(() => {
        if (actions.length > 0 && appState === STATES.LISTENING) {
            setAppState(STATES.ACTIVITY);
        }
    }, [actions.length]);

    // YELLOW confirm
    useEffect(() => {
        if (pendingYellow && appState !== STATES.YELLOW_PAUSE) {
            setPrevState(appState);
            setAppState(STATES.YELLOW_PAUSE);
        }
    }, [pendingYellow]);

    // RED auth
    useEffect(() => {
        if (pendingRed && !pendingRed._result && appState !== STATES.RED_AUTH) {
            setPrevState(appState);
            setAppState(STATES.RED_AUTH);
        }
    }, [pendingRed]);

    // ── Callbacks ──────────────────────────────────────────────────────
    function handleStart() {
        setAppState(STATES.LISTENING);
    }

    function handleStop() {
        setAppState(STATES.IDLE);
    }

    function handleYellowResolve() {
        clearPendingYellow();
        setAppState(STATES.ACTIVITY);
    }

    function handleRedApproved() {
        clearPendingRed();
        setAppState(STATES.ACTIVITY);
    }

    function handleRedDenied() {
        clearPendingRed();
        setAppState(STATES.ACTIVITY);
    }

    // ── Render ─────────────────────────────────────────────────────────
    return (
        <div className="app-shell">
            {/* Layer 1: Base page */}
            {appState === STATES.IDLE && (
                <IdlePage
                    isConnected={isConnected}
                    onStart={handleStart}
                />
            )}
            {(appState === STATES.LISTENING) && (
                <ListeningPage
                    waveform={waveform}
                    sessionSeconds={sessionSeconds}
                    agentStatus={status}
                    onStop={handleStop}
                />
            )}
            {(appState === STATES.ACTIVITY || appState === STATES.YELLOW_PAUSE || appState === STATES.RED_AUTH) && (
                <ActivityPage
                    actions={actions}
                    sessionSeconds={sessionSeconds}
                    agentStatus={status}
                    onStop={handleStop}
                />
            )}

            {/* Layer 2: YELLOW overlay */}
            {appState === STATES.YELLOW_PAUSE && pendingYellow && (
                <YellowPausePage
                    pending={pendingYellow}
                    actions={actions}
                    sessionSeconds={sessionSeconds}
                    sendMessage={sendMessage}
                    onResolve={handleYellowResolve}
                />
            )}

            {/* Layer 3: RED AUTH overlay */}
            {appState === STATES.RED_AUTH && pendingRed && (
                <RedAuthPage
                    pending={pendingRed}
                    onApproved={handleRedApproved}
                    onDenied={handleRedDenied}
                />
            )}
        </div>
    );
}
