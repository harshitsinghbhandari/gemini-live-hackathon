// App.jsx
// App State Machine: MIRROR ←→ RED_AUTH → POST_AUTH → MIRROR

import React, { useState } from 'react';
import { usePendingAuth } from './hooks/usePendingAuth.js';
import { MirrorPage } from './pages/MirrorPage.jsx';
import { RedAuthPage } from './pages/RedAuthPage.jsx';
import { PostAuthPage } from './pages/PostAuthPage.jsx';
import PinGate from './components/PinGate.jsx';
import { CONFIG } from './config.js';

const STATES = {
    MIRROR: 'MIRROR',
    RED_AUTH: 'RED_AUTH',
    POST_AUTH: 'POST_AUTH'
};

export default function App() {
    const [appState, setAppState] = useState(STATES.MIRROR);
    const [authResult, setAuthResult] = useState(null); // 'approved' or 'denied'

    // Only poll if we are in MIRROR mode
    const { pendingReq, clearPending } = usePendingAuth(appState === STATES.MIRROR);

    // If a pending request comes in while MIRROR, transition to RED_AUTH
    if (pendingReq && appState === STATES.MIRROR) {
        setAppState(STATES.RED_AUTH);
    }

    // Effect to register service worker
    React.useEffect(() => {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(() => { });
        }
    }, []);

    const handleResolveAuth = (result) => {
        setAuthResult(result);
        setAppState(STATES.POST_AUTH);
        clearPending();
    };

    const handlePostAuthDismiss = () => {
        setAuthResult(null);
        setAppState(STATES.MIRROR);
    };

    return (
        <PinGate backendUrl={CONFIG.BACKEND_URL}>
            <div className="app-shell">
                {appState === STATES.MIRROR && (
                    <MirrorPage />
                )}

                {appState === STATES.RED_AUTH && pendingReq && (
                    <RedAuthPage
                        request={pendingReq}
                        onResolve={handleResolveAuth}
                    />
                )}

                {appState === STATES.POST_AUTH && (
                    <PostAuthPage
                        result={authResult}
                        onDismiss={handlePostAuthDismiss}
                    />
                )}
            </div>
        </PinGate>
    );
}
