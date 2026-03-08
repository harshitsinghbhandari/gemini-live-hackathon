export function TierBadge({ tier }) {
    const isRed = tier === 'RED';
    const isYellow = tier === 'YELLOW';
    const isGreen = tier === 'GREEN' || !tier;

    return (
        <span className={`inline-flex items-center justify-center px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest border font-mono ${
            isRed ? 'bg-red-500/10 text-red-500 border-red-500/20' :
            isYellow ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
            'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
        }`}>
            {tier || 'GREEN'}
        </span>
    );
}
