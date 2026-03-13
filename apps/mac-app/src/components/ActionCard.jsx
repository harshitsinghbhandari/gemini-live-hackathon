import { useState } from 'react';
import { TierBadge } from './TierBadge.jsx';
import { formatDuration, formatTimestamp, toolkitLabel } from '../utils/formatters.js';

export function ActionCard({ action, dim }) {
    const [expanded, setExpanded] = useState(false);
    const timestamp = action.timestamp ? formatTimestamp(action.timestamp) : '';

    return (
        <div
            onClick={() => setExpanded(!expanded)}
            className={`group relative flex flex-col px-6 py-4 gap-3 rounded-xl bg-surface-dark border-l-[4px] transition-all duration-200 cursor-pointer ${
                action.tier === 'RED' ? 'border-accent-red' :
                action.tier === 'YELLOW' ? 'border-amber-accent' :
                'border-sage'
            } ${dim ? 'opacity-40 grayscale-[0.5] hover:opacity-100 hover:grayscale-0' : 'opacity-100'} shadow-lg hover:bg-slate-800/40`}
        >
            <div className="flex items-center gap-5 w-full">
                <div className="flex flex-col shrink-0 min-w-[72px]">
                    <span className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-tighter">{timestamp}</span>
                    <TierBadge tier={action.tier} className="mt-1" />
                </div>

                <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <p className="text-sm font-bold truncate text-slate-100 uppercase tracking-tight leading-tight">
                        {action.action || action.speak || '—'}
                    </p>
                    <p className="text-[10px] font-mono font-bold text-slate-500 mt-1 uppercase tracking-widest truncate">
                        {action.tool || 'SYSTEM'} // {action.toolkit || 'CORE'}
                    </p>
                </div>

                <div className="shrink-0 flex items-center justify-center">
                    {action.blocked ? (
                        <span className="material-symbols-outlined text-accent-red text-xl font-bold">cancel</span>
                    ) : action.success ? (
                        <span className="material-symbols-outlined text-sage text-xl font-bold">check_circle</span>
                    ) : action.auth_used ? (
                        <span className="material-symbols-outlined text-primary text-xl font-bold">lock</span>
                    ) : (
                        <div className="size-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                    )}
                </div>
            </div>

            {expanded && (
                <div className="mt-2 pt-3 border-t border-slate-700/50 space-y-3 animate-in fade-in slide-in-from-top-1 duration-200">
                    {action.reason && (
                        <div className="flex flex-col gap-1">
                            <span className="text-[9px] font-black uppercase text-slate-500 tracking-widest">Reason</span>
                            <p className="text-xs text-slate-300 font-medium italic">"{action.reason}"</p>
                        </div>
                    )}
                    {action.error && (
                        <div className="flex flex-col gap-1 p-2 rounded bg-red-500/10 border border-red-500/20">
                            <span className="text-[9px] font-black uppercase text-red-500 tracking-widest">Error</span>
                            <p className="text-xs text-red-200 font-mono">{action.error}</p>
                        </div>
                    )}
                    {action.arguments && (
                        <div className="flex flex-col gap-1">
                            <span className="text-[9px] font-black uppercase text-slate-500 tracking-widest">Arguments</span>
                            <pre className="text-[10px] font-mono p-3 rounded bg-black/40 text-primary overflow-x-auto custom-scrollbar">
                                {JSON.stringify(action.arguments, null, 2)}
                            </pre>
                        </div>
                    )}
                    {action.duration_ms != null && (
                        <div className="flex items-center justify-between text-[9px] font-black text-slate-500 uppercase tracking-widest">
                            <span>Duration</span>
                            <span>{formatDuration(action.duration_ms)}</span>
                        </div>
                    )}
                </div>
            )}

            {/* Hover subtle glow */}
            <div className={`absolute inset-0 opacity-0 group-hover:opacity-5 pointer-events-none transition-opacity duration-300 rounded-r-xl ${
                action.tier === 'RED' ? 'bg-accent-red' :
                action.tier === 'YELLOW' ? 'bg-amber-accent' :
                'bg-sage'
            }`} />
        </div>
    );
}
