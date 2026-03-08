import { useState, useEffect } from 'react';
import { CONFIG } from '../config.js';

export function IdlePage({ isConnected, onStart }) {
    const [helperReady, setHelperReady] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Poll helper health every 5 seconds
    useEffect(() => {
        let alive = true;
        async function checkHelper() {
            try {
                const r = await fetch(`${CONFIG.HELPER_URL}/health`, { signal: AbortSignal.timeout(1500) });
                if (alive) setHelperReady(r.ok);
            } catch {
                if (alive) setHelperReady(false);
            }
        }
        checkHelper();
        const interval = setInterval(checkHelper, 5000);
        return () => { alive = false; clearInterval(interval); };
    }, []);

    async function handleStart() {
        if (loading) return;
        if (!helperReady) {
            setError('Start helper server first:\npython aegis/helper_server.py');
            setTimeout(() => setError(''), 4000);
            return;
        }
        setLoading(true);
        setError('');
        try {
            const r = await fetch(`${CONFIG.HELPER_URL}/start`, {
                method: 'POST',
                signal: AbortSignal.timeout(3000),
            });
            const json = await r.json();
            if (json.started || json.reason === 'already running') {
                onStart();
            } else {
                setError('Failed to start agent');
                setTimeout(() => setError(''), 4000);
            }
        } catch {
            setError('Helper server unreachable');
            setTimeout(() => setError(''), 4000);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-display relative overflow-hidden">
            {/* macOS style Traffic Lights (Visual only) */}
            <div className="absolute top-4 left-4 flex gap-2">
                <div className="w-3 h-3 rounded-full bg-slate-700/50"></div>
                <div className="w-3 h-3 rounded-full bg-slate-700/50"></div>
                <div className="w-3 h-3 rounded-full bg-slate-700/50"></div>
            </div>

            <div className="layout-container flex h-full grow flex-col items-center justify-center px-6">
                <div className="w-full max-w-[440px] flex flex-col items-center">
                    {/* Logo Section */}
                    <div className="mb-12 flex flex-col items-center">
                        <div className="w-20 h-20 mb-6 flex items-center justify-center rounded-2xl bg-slate-800/40 border border-slate-700/50">
                            <span className="material-symbols-outlined text-slate-400 !text-5xl">shield</span>
                        </div>
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-100">Aegis</h1>
                        <p className="text-slate-500 mt-2 text-sm">Secure local environment</p>
                    </div>

                    {/* Status List */}
                    <div className="w-full space-y-2 mb-10">
                        {/* Status Row 1 */}
                        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/20 border border-slate-800/50">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-800/40 text-slate-400">
                                    <span className="material-symbols-outlined !text-xl">database</span>
                                </div>
                                <span className="text-slate-300 text-sm font-medium">Helper Server</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-slate-500 text-xs">{helperReady ? 'Online' : 'Offline'}</span>
                                <div className={`w-2 h-2 rounded-full ${helperReady ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-600'}`}></div>
                            </div>
                        </div>

                        {/* Status Row 2 */}
                        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/20 border border-slate-800/50">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-800/40 text-slate-400">
                                    <span className="material-symbols-outlined !text-xl">person</span>
                                </div>
                                <span className="text-slate-300 text-sm font-medium">Agent</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-slate-500 text-xs">{isConnected ? 'Connected' : 'Disconnected'}</span>
                                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-600'}`}></div>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="w-full flex flex-col gap-3">
                        <button
                            className={`w-full h-12 flex items-center justify-center rounded-lg border border-slate-700 transition-colors font-medium text-sm ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-800/50 text-slate-200'}`}
                            onClick={handleStart}
                            disabled={loading}
                        >
                            {loading ? 'Starting Session...' : 'Start Session'}
                        </button>
                        <div className="flex items-center justify-center gap-4 mt-4">
                            <button className="flex items-center gap-1 text-slate-500 hover:text-slate-300 text-xs transition-colors">
                                <span className="material-symbols-outlined !text-sm">settings</span>
                                Preferences
                            </button>
                            <button className="flex items-center gap-1 text-slate-500 hover:text-slate-300 text-xs transition-colors">
                                <span className="material-symbols-outlined !text-sm">help</span>
                                Documentation
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Error toast */}
            {error && (
                <div className="fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-xs whitespace-pre-line z-50">
                    {error}
                </div>
            )}

            {/* Footer Decoration */}
            <div className="absolute bottom-8 w-full flex justify-center opacity-20 pointer-events-none">
                <div className="w-96 h-px bg-gradient-to-r from-transparent via-slate-500 to-transparent"></div>
            </div>
        </div>
    );
}
