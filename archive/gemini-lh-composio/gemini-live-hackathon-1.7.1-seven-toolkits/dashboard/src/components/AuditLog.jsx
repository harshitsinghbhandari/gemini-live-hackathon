import React from 'react';
import TierBadge from './TierBadge';
import { formatTimestamp, formatAction, getToolkitName } from '../utils/formatters';

const AuditLog = ({ entries, onSelect, selectedId }) => {
  if (entries.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-slate-500 gap-4">
        <div className="text-4xl">📜</div>
        <div className="text-sm font-medium tracking-tight">No actions logged yet. Start talking to Aegis.</div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      <div className="px-6 py-4 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 flex border-b border-purple-500/10">
        <span className="w-20">Time</span>
        <span className="w-28">Tier</span>
        <span className="flex-1">Action</span>
        <span className="w-32">Toolkit</span>
        <span className="w-20 text-center">Auth</span>
        <span className="w-16 text-center">Status</span>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {entries.map((entry, idx) => {
          const isSelected = selectedId === entry.id;
          return (
            <div
              key={entry.id || idx}
              onClick={() => onSelect(entry)}
              className={`flex items-center px-6 py-4 border-b border-purple-500/5 cursor-pointer transition-all hover:bg-white/5 active:bg-purple-500/10 animate-slide-in ${isSelected ? 'bg-purple-500/10 border-l-2 border-l-purple-500' : ''}`}
              style={{ animationDelay: `${idx * 0.05}s` }}
            >
              <div className="w-20 text-[11px] font-mono text-slate-400">
                {formatTimestamp(entry.timestamp)}
              </div>
              <div className="w-28">
                <TierBadge tier={entry.tier} />
              </div>
              <div className="flex-1 text-sm font-medium tracking-tight">
                {formatAction(entry.action)}
              </div>
              <div className="w-32 text-[10px] font-bold tracking-widest text-slate-400">
                {getToolkitName(entry.toolkit || entry.tool)}
              </div>
              <div className="w-20 flex justify-center text-lg">
                {entry.auth_used && <span>🔐</span>}
                {entry.confirmed_verbally && <span>💬</span>}
                {!entry.auth_used && !entry.confirmed_verbally && <span className="text-slate-700 opacity-20">—</span>}
              </div>
              <div className="w-16 flex justify-center text-lg">
                {entry.success ? <span className="text-green-500">✓</span> : <span className="text-red-500">🚫</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AuditLog;
