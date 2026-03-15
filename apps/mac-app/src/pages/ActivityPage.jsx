import { CONFIG } from '../config.js';
import { ActionCard } from '../components/ActionCard.jsx';
import { SessionTimer } from '../components/SessionTimer.jsx';

export function ActivityPage({ actions, sessionSeconds, agentStatus, onStop }) {
    const [stopping, setStopping] = useState(false);

    async function handleStop() {
        if (stopping) return;
        setStopping(true);
        try {
            await fetch(`${CONFIG.HELPER_URL}/stop`, { method: 'POST', signal: AbortSignal.timeout(3000) });
        } catch {/* ignore */ }
        onStop();
        setStopping(false);
    }

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 antialiased overflow-hidden min-h-screen relative flex w-full flex-col">
            {/* Top Navigation Bar */}
            <header className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-background-light/50 dark:bg-background-dark/50 backdrop-blur-md px-6 py-3 shrink-0">
                <div className="flex items-center gap-8">
                    <div className="flex items-center gap-3">
                        <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white">
                            <span className="material-symbols-outlined text-xl">shield</span>
                        </div>
                        <h2 className="text-slate-900 dark:text-slate-100 text-lg font-bold tracking-tight uppercase">Aegis</h2>
                    </div>
                </div>
            </header>

            <main className="flex flex-1 overflow-hidden">
                {/* Sidebar Navigation */}
                <aside className="w-64 border-r border-slate-200 dark:border-slate-800 flex flex-col p-4 bg-slate-50 dark:bg-background-dark shrink-0">
                    <div className="flex items-center gap-3 mb-8 px-2">
                        <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                            <span className="material-symbols-outlined">terminal</span>
                        </div>
                        <div>
                            <p className="text-sm font-semibold">Aegis Core</p>
                            <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">v2.4.0</p>
                        </div>
                    </div>
                    <div className="space-y-1">
                        <a className="flex items-center gap-3 px-3 py-2 rounded-lg bg-primary/10 text-primary border border-primary/10" href="#">
                            <span className="material-symbols-outlined text-[20px]">play_arrow</span>
                            <span className="text-sm font-medium">Active Session</span>
                        </a>
                    </div>
                    <div className="mt-auto p-4 rounded-xl bg-primary/5 border border-primary/10">
                        <p className="text-xs font-bold text-primary uppercase tracking-wider mb-2">Agent Status</p>
                        <div className="flex items-center gap-2 mb-1">
                            <div className={`size-2 rounded-full ${agentStatus === 'idle' ? 'bg-slate-600' : 'bg-emerald-500 animate-pulse'}`}></div>
                            <p className="text-xs font-medium uppercase">{agentStatus}</p>
                        </div>
                    </div>
                </aside>

                {/* Main Execution Area */}
                <section className="flex-1 flex overflow-hidden">
                    {/* Left: Info & Control */}
                    <div className="w-1/2 flex flex-col border-r border-slate-200 dark:border-slate-800">
                        <div className="p-8">
                            <h1 className="text-3xl font-bold tracking-tight mb-2 uppercase">Execution Feed</h1>
                            <p className="text-slate-500 dark:text-slate-400 flex items-center gap-2 text-sm font-medium">
                                <span className="material-symbols-outlined text-sm text-primary animate-spin">sync</span>
                                Security protocols active and monitoring...
                            </p>
                        </div>

                        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                            <div className="w-20 h-20 mb-6 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
                                <span className="material-symbols-outlined text-primary text-4xl">shield</span>
                            </div>
                            <h2 className="text-xl font-bold mb-2 uppercase">Secure Gateway</h2>
                            <p className="text-slate-500 text-sm max-w-sm">Every action is classified and validated against your defined security boundaries.</p>
                        </div>

                        <div className="p-8 mt-auto border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div className="flex gap-4">
                                <div className="text-center">
                                    <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-bold">Duration</p>
                                    <SessionTimer seconds={sessionSeconds} className="font-mono text-lg font-bold" />
                                </div>
                            </div>
                            <button
                                onClick={handleStop}
                                disabled={stopping}
                                className={`bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white px-6 py-2 rounded-lg font-bold text-xs transition-all border border-red-500/20 uppercase tracking-widest ${stopping ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                {stopping ? 'Stopping...' : 'Stop Process'}
                            </button>
                        </div>
                    </div>

                    {/* Right: Action Cards Feed */}
                    <div className="w-1/2 bg-slate-50 dark:bg-background-dark/30 flex flex-col">
                        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-background-light dark:bg-background-dark">
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Live Action Feed</h3>
                            <span className="text-[10px] font-mono bg-primary/20 text-primary px-2 py-0.5 rounded uppercase font-bold tracking-widest">Live</span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                            {actions.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 opacity-50">
                                    <span className="material-symbols-outlined text-4xl">inbox</span>
                                    <p className="text-xs font-bold uppercase tracking-widest">Waiting for input...</p>
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
                    </div>
                </section>
            </main>
        </div>
    );
}
