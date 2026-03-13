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
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 antialiased overflow-hidden min-h-screen relative flex w-full flex-col">
            {/* Top Navigation Bar */}
            <header className="flex items-center justify-between border-b border-slate-800/50 bg-[#161B22] px-6 py-3">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 text-primary">
                        <span className="material-symbols-outlined text-3xl">shield_with_heart</span>
                        <h2 className="text-slate-100 text-lg font-bold leading-tight tracking-tight uppercase">Aegis</h2>
                    </div>
                    <div className="h-6 w-[1px] bg-slate-700"></div>
                    <div className="flex items-center h-9 w-64 bg-slate-800/50 rounded-lg px-3 border border-slate-700 opacity-50">
                        <span className="material-symbols-outlined text-slate-400 text-sm">search</span>
                        <input className="bg-transparent border-none focus:ring-0 text-sm text-slate-200 w-full placeholder:text-slate-500" placeholder="Search security logs..." type="text" disabled />
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex gap-1 opacity-50">
                        <button className="p-2 hover:bg-slate-700/50 rounded-lg text-slate-400 transition-colors">
                            <span className="material-symbols-outlined">settings</span>
                        </button>
                        <button className="p-2 hover:bg-slate-700/50 rounded-lg text-slate-400 transition-colors">
                            <span className="material-symbols-outlined">notifications</span>
                        </button>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
                        <span className="material-symbols-outlined text-primary text-xl">admin_panel_settings</span>
                    </div>
                </div>
            </header>

            <main className="flex flex-1 overflow-hidden opacity-30 blur-sm pointer-events-none">
                <aside className="w-64 border-r border-slate-800/50 bg-[#0D1117] flex flex-col p-4 gap-2">
                    <div className="mb-6 px-3">
                        <h1 className="text-slate-100 text-sm font-semibold">Aegis OS v4.2</h1>
                    </div>
                    <nav className="space-y-1">
                        <a className="flex items-center gap-3 px-3 py-2 text-primary bg-primary/10 rounded-lg border border-primary/20">
                            <span className="material-symbols-outlined text-[20px]">pending_actions</span>
                            <span className="text-sm font-medium">Action Center</span>
                        </a>
                    </nav>
                </aside>
                <section className="flex-1 flex flex-col bg-[#0D1117] p-8 overflow-y-auto">
                    <div className="max-w-4xl mx-auto w-full">
                        <header className="mb-10">
                            <h2 className="text-slate-100 text-3xl font-bold tracking-tight uppercase">Security Intercept</h2>
                        </header>
                    </div>
                </section>
                <aside className="w-80 border-l border-slate-800/50 bg-[#161B22] flex flex-col">
                    <div className="p-4 border-b border-slate-800/50 flex justify-between items-center">
                        <h3 className="text-slate-100 text-sm font-bold uppercase tracking-widest">Feed</h3>
                    </div>
                </aside>
            </main>

            {/* Overlay Section (Modal Centerpiece) */}
            <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/60 backdrop-blur-md">
                <div className="max-w-2xl w-full bg-[#1C2128] rounded-xl border-l-4 border-amber-accent shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                    <div className="p-8">
                        <div className="flex items-start justify-between gap-6">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 text-amber-accent mb-2">
                                    <span className="material-symbols-outlined">pause_circle</span>
                                    <span className="text-xs font-bold uppercase tracking-widest">Security Alert</span>
                                </div>
                                <h3 className="text-slate-100 text-2xl font-bold leading-tight mb-2 uppercase">Confirmation Needed</h3>
                                <p className="text-slate-400 text-lg mb-6 leading-relaxed">
                                    {pending?.question || pending?.speak || 'Shall I proceed with this action?'}
                                </p>

                                {pending?.action && (
                                    <div className="mb-8 p-4 rounded-lg bg-slate-900/50 border border-slate-800">
                                        <p className="font-mono text-sm text-amber-accent leading-relaxed">
                                            {pending.action}
                                        </p>
                                    </div>
                                )}

                                <div className="flex gap-4">
                                    <button
                                        onClick={() => respond(true)}
                                        className="bg-amber-accent hover:bg-amber-600 text-white px-8 py-3 rounded-lg font-bold text-sm transition-all flex items-center gap-2 uppercase tracking-widest"
                                    >
                                        <span className="material-symbols-outlined text-sm">check_circle</span>
                                        Proceed
                                    </button>
                                    <button
                                        onClick={() => respond(false)}
                                        className="bg-slate-700/50 hover:bg-slate-700 text-slate-200 px-8 py-3 rounded-lg font-bold text-sm transition-all uppercase tracking-widest"
                                    >
                                        Skip Action
                                    </button>
                                </div>
                            </div>
                            <div className="hidden lg:flex w-40 h-40 bg-slate-800/50 rounded-xl items-center justify-center border border-slate-700 shrink-0">
                                <span className="material-symbols-outlined text-amber-accent/30 text-7xl">security</span>
                            </div>
                        </div>
                    </div>
                    <div className="px-8 py-4 bg-slate-900/40 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em]">
                        <span>Session active</span>
                        <SessionTimer seconds={sessionSeconds} />
                    </div>
                </div>
            </div>
        </div>
    );
}
