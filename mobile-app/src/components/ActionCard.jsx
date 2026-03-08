import { TierBadge } from './TierBadge.jsx';

export function ActionCard({ action }) {
    const timestamp = action.timestamp ? new Date(action.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '';

    return (
        <div className={`flex items-center px-5 py-4 gap-4 rounded-xl bg-slate-800/20 border-l-[4px] border border-slate-700/50 ${
            action.tier === 'RED' ? 'border-l-danger' :
            action.tier === 'YELLOW' ? 'border-l-amber' :
            'border-l-sage'
        }`}>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-tighter">{timestamp}</span>
                    <TierBadge tier={action.tier} />
                </div>
                <p className="text-sm font-bold text-slate-100 truncate uppercase tracking-tight">
                    {action.action}
                </p>
            </div>
            <div className="shrink-0">
                {action.success ? (
                    <span className="material-symbols-outlined text-sage text-xl">check_circle</span>
                ) : action.blocked ? (
                    <span className="material-symbols-outlined text-danger text-xl">cancel</span>
                ) : (
                    <div className="size-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                )}
            </div>
        </div>
    );
}
