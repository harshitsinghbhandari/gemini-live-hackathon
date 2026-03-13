import { useEffect, useRef, useState } from 'react';
import { CountdownBar } from '../components/CountdownBar.jsx';
import { CONFIG } from '../config.js';

const AUTH_TIMEOUT = 30; // seconds

export function RedAuthPage({ pending, onApproved, onDenied }) {
    const [elapsed, setElapsed] = useState(0);
    const [flash, setFlash] = useState(''); // '' | 'approve' | 'deny'
    const donRef = useRef(false);

    // Sync to pending timestamp
    useEffect(() => {
        if (pending?.timestamp) {
            const start = new Date(pending.timestamp).getTime();
            const now = Date.now();
            const diff = Math.floor((now - start) / 1000);
            setElapsed(Math.max(0, diff));
        }
    }, [pending?.timestamp]);

    // Tick elapsed seconds
    useEffect(() => {
        const id = setInterval(() => {
            setElapsed((e) => {
                const next = e + 1;
                if (next >= AUTH_TIMEOUT) {
                    clearInterval(id);
                    if (!donRef.current) {
                        donRef.current = true;
                        onDenied(true);
                    }
                }
                return next;
            });
        }, 1000);
        return () => clearInterval(id);
    }, [onDenied]);

    // Poll backend /auth/status/{request_id} every 2s
    useEffect(() => {
        if (!pending?.request_id) return;
        let alive = true;
        async function poll() {
            try {
                const r = await fetch(
                    `${CONFIG.BACKEND_URL}/auth/status/${pending.request_id}`,
                    {
                        headers: { "X-User-ID": CONFIG.USER_ID },
                        signal: AbortSignal.timeout(3000)
                    }
                );
                if (!alive) return;
                if (r.ok) {
                    const data = await r.json();
                    if (data.status === 'approved' && !donRef.current) {
                        donRef.current = true;
                        setFlash('approve');
                        setTimeout(onApproved, 800);
                    } else if (data.status === 'denied' && !donRef.current) {
                        donRef.current = true;
                        setFlash('deny');
                        setTimeout(() => onDenied(false), 800);
                    }
                }
            } catch {/* network errors — keep polling */ }
        }
        const id = setInterval(poll, 2000);
        poll(); // immediate first poll
        return () => { alive = false; clearInterval(id); };
    }, [pending, onApproved, onDenied]);

    // Also react to WebSocket red_auth_result (surfaced via pending._result)
    useEffect(() => {
        if (pending?._result != null && !donRef.current) {
            donRef.current = true;
            if (pending._result) {
                setFlash('approve');
                setTimeout(onApproved, 800);
            } else {
                setFlash('deny');
                setTimeout(() => onDenied(false), 800);
            }
        }
    }, [pending, onApproved, onDenied]);

    const remaining = AUTH_TIMEOUT - elapsed;

    return (
        <div className={`fixed inset-0 z-[100] bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center overflow-hidden transition-colors duration-500 ${flash === 'approve' ? 'bg-emerald-500/20' : flash === 'deny' ? 'bg-red-500/20' : ''}`}>
            {/* Background Overlay (Simulating 40% dimmed macOS background) */}
            <div className="fixed inset-0 bg-black/40 z-0 backdrop-blur-sm"></div>

            {/* Main Desktop App Container (1440x900 simulation) */}
            <div className="relative z-10 w-full max-w-[1440px] h-screen flex items-center justify-center p-6">
                {/* Large Modal Card */}
                <div className="w-full max-w-[560px] bg-background-light dark:bg-card-dark border border-slate-200 dark:border-accent-red/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-300">
                    {/* Top Navigation / Header Area */}
                    <header className="flex items-center justify-between px-8 py-6 border-b border-slate-200 dark:border-slate-800">
                        <div className="flex items-center gap-3">
                            <div className="text-primary">
                                <span className="material-symbols-outlined text-3xl">security</span>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight dark:text-slate-100 uppercase">Authorization Required</h1>
                        </div>
                        <div className="flex gap-2">
                            <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-700/50">
                                <span className="material-symbols-outlined text-sm">notifications</span>
                            </div>
                        </div>
                    </header>

                    {/* Main Content Section */}
                    <div className="p-8 flex flex-col items-center text-center">
                        {/* Visual Indicator */}
                        <div className="w-full h-48 mb-8 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800/50 flex items-center justify-center relative">
                            <div className="absolute inset-0 opacity-20 bg-gradient-to-t from-accent-red to-transparent"></div>
                            <span className={`material-symbols-outlined text-6xl text-accent-red ${flash ? '' : 'animate-pulse'}`}>
                                {flash === 'approve' ? 'verified_user' : flash === 'deny' ? 'dangerous' : 'fingerprint'}
                            </span>
                            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCGnsZeOYhR7nJvtsja4SAYHTzr_JnP17u0M1Liqh0Vo3UzlRWAmUhEkSukr6gGLV-G7UdWCBljvlo4Xls-XWwN_wJhdOB33BKeLSm_YiPEtQ2-PQjGUhUrjkvbh1iQxluzVFRbTDmmIC4fhLqPioXq8n9muheJYeWPY5HzGyoYWjELpnWTGAajPPyyO5kucAFL6hibvXhoSE36SRz1N8gJmzo0U19Mi41nqH1zydcQoLL_-UmKdwzVp8O3gggMlaF-h9Zx1dcQdSyw')", backgroundSize: 'cover', backgroundPosition: 'center', mixBlendMode: 'overlay' }}></div>
                        </div>

                        <div className="space-y-4 max-w-md">
                            <p className="text-lg font-medium text-slate-800 dark:text-slate-200 leading-relaxed uppercase tracking-tight">
                                {pending?.action || 'A critical system action has been requested.'}
                            </p>
                            <p className="text-sm text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest italic opacity-80">
                                {pending?.reason || 'Sent to mobile for biometric approval'}
                            </p>
                        </div>

                        {/* Monospace Countdown Timer */}
                        <div className="mt-10 flex items-center gap-4">
                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center border border-slate-200 dark:border-slate-700">
                                    <span className={`text-2xl font-mono font-medium ${remaining <= 10 ? 'text-red-500' : 'text-primary'}`}>
                                        00
                                    </span>
                                </div>
                                <span className="text-[10px] uppercase tracking-widest mt-2 text-slate-500 font-bold">Minutes</span>
                            </div>
                            <div className="text-2xl font-mono text-slate-400 mb-6">:</div>
                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center border border-slate-200 dark:border-slate-700">
                                    <span className={`text-2xl font-mono font-medium ${remaining <= 10 ? 'text-red-500' : 'text-primary'}`}>
                                        {remaining.toString().padStart(2, '0')}
                                    </span>
                                </div>
                                <span className="text-[10px] uppercase tracking-widest mt-2 text-slate-500 font-bold">Seconds</span>
                            </div>
                        </div>

                        <div className="mt-8 flex flex-col items-center gap-6 w-full">
                            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-widest">
                                <span className={`material-symbols-outlined text-xs ${flash ? '' : 'animate-spin'}`}>
                                    {flash ? 'check' : 'sync'}
                                </span>
                                <span>{flash ? 'Response Received' : 'Waiting for mobile response...'}</span>
                            </div>
                            <button
                                onClick={() => onDenied(false)}
                                className="text-slate-500 dark:text-slate-400 hover:text-accent-red dark:hover:text-accent-red transition-all text-xs font-bold uppercase tracking-widest border-b border-transparent hover:border-accent-red pb-0.5"
                            >
                                Cancel Action
                            </button>
                        </div>
                    </div>

                    {/* Footer Meta */}
                    <footer className="px-8 py-4 bg-slate-50 dark:bg-slate-900/50 flex justify-between items-center border-t border-slate-200 dark:border-slate-800">
                        <div className="flex items-center gap-2 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                            <span className="material-symbols-outlined text-xs">location_on</span>
                            <span>Requested locally</span>
                        </div>
                        <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold font-mono">
                            ID: {pending?.request_id?.slice(0, 8).toUpperCase() || 'AE-AUTH'}
                        </div>
                    </footer>
                </div>
            </div>
        </div>
    );
}
