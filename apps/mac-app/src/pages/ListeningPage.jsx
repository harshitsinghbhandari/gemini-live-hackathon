import { CONFIG } from '../config.js';
import { SessionTimer } from '../components/SessionTimer.jsx';

export function ListeningPage({ waveform, sessionSeconds, onStop, agentStatus }) {
    async function handleStop() {
        try {
            await fetch(`${CONFIG.HELPER_URL}/stop`, { method: 'POST', signal: AbortSignal.timeout(3000) });
        } catch {/* ignore */ }
        onStop();
    }

    const peak = Math.max(...waveform) || 0.05;

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 antialiased selection:bg-primary/30 relative flex min-h-screen w-full flex-col overflow-x-hidden">
            <div className="layout-container flex h-full grow flex-col items-center">
                <header className="flex w-full items-center justify-between px-8 py-6 max-w-[1440px]">
                    <div className="flex items-center gap-3">
                        <div className="text-primary">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                                <path d="M42.4379 44C42.4379 44 36.0744 33.9038 41.1692 24C46.8624 12.9336 42.2078 4 42.2078 4L7.01134 4C7.01134 4 11.6577 12.932 5.96912 23.9969C0.876273 33.9029 7.27094 44 7.27094 44L42.4379 44Z" fill="currentColor"></path>
                            </svg>
                        </div>
                        <h2 className="text-slate-100 text-xl font-bold tracking-tight">Aegis</h2>
                    </div>
                    <div className="flex gap-3 items-center">
                        <SessionTimer seconds={sessionSeconds} />
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></div>
                    </div>
                </header>

                <main className="flex flex-1 flex-col items-center justify-center w-full max-w-[960px] px-6">
                    <div className="relative flex items-center justify-center w-80 h-80 mb-16">
                        <div className="absolute inset-0 rounded-full border border-slate-800/50 scale-125"></div>
                        <div className="absolute inset-0 rounded-full border border-slate-800 scale-100"></div>
                        <div className="absolute inset-0 rounded-full border border-primary/20 scale-75"></div>

                        {/* Dynamic Waveform Visualizer */}
                        <div className="flex items-center gap-1.5 h-32">
                            {waveform.slice(-12).map((v, i) => (
                                <div
                                    key={i}
                                    className="w-1 bg-primary rounded-full transition-all duration-100"
                                    style={{
                                        height: `${Math.max(8, v * 128)}px`,
                                        opacity: 0.3 + (v * 0.7)
                                    }}
                                />
                            ))}
                        </div>
                    </div>

                    <div className="w-full max-w-md bg-surface-dark border border-slate-800/50 rounded-xl p-6 mb-12">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="material-symbols-outlined text-primary text-sm">graphic_eq</span>
                            <p className="text-slate-400 text-[11px] font-bold tracking-widest uppercase">Agent Status</p>
                        </div>
                        <div className="space-y-2 font-mono text-sm leading-relaxed">
                            <div className="flex items-center gap-1">
                                <span className="text-primary/60">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
                                <span className="text-slate-100 uppercase tracking-wide">
                                    {agentStatus === 'executing' ? 'Executing action...' :
                                     agentStatus === 'auth' ? 'Awaiting authorization...' :
                                     'Aegis is listening...'}
                                </span>
                                <span className="w-1.5 h-4 bg-primary animate-pulse ml-0.5"></span>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col items-center gap-4">
                        <button
                            onClick={handleStop}
                            className="flex items-center justify-center px-8 py-3 rounded-full bg-slate-800/30 hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 transition-all duration-200 group border border-slate-700/50"
                        >
                            <span className="material-symbols-outlined text-sm mr-2 group-hover:text-red-400 transition-colors">stop_circle</span>
                            <span className="text-sm font-semibold tracking-wide uppercase">Stop Session</span>
                        </button>
                        <p className="text-slate-600 text-[10px] font-medium tracking-[0.2em] uppercase">Press ESC to cancel</p>
                    </div>
                </main>

                <footer className="w-full py-8 flex justify-center opacity-30">
                    <div className="flex gap-8">
                        <div className="w-32 h-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent"></div>
                    </div>
                </footer>
            </div>
        </div>
    );
}
