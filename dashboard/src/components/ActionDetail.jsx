import React from 'react';
import TierBadge from './TierBadge';
import { formatTimestamp, formatDuration, formatArguments } from '../utils/formatters';

const ActionDetail = ({ entry, onClose }) => {
  if (!entry) {
    return (
      <div className="w-[400px] border-l border-purple-500/10 flex flex-col items-center justify-center p-12 text-slate-500 gap-4">
        <div className="text-4xl">🔍</div>
        <div className="text-sm font-medium tracking-tight">Select an action to see details</div>
      </div>
    );
  }

  return (
    <div className="w-[400px] border-l border-purple-500/20 bg-background/30 backdrop-blur-xl flex flex-col animate-slide-in">
      <div className="p-6 border-b border-purple-500/10 flex items-center justify-between">
        <h3 className="text-lg font-bold">Action Detail</h3>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors p-2 rounded-full hover:bg-white/5"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Action</label>
          <p className="text-sm font-medium leading-relaxed">{entry.action}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Tier & Reason</label>
            <TierBadge tier={entry.tier} />
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Tool</label>
            <p className="text-[11px] font-mono font-bold text-purple-400">{entry.tool}</p>
            <p className="text-[10px] text-slate-500">{entry.toolkit || 'SYSTEM'}</p>
          </div>
        </div>

        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Arguments</label>
          <pre className="text-[11px] font-mono bg-black/40 p-3 rounded-lg border border-purple-500/5 overflow-x-auto text-purple-200">
            {formatArguments(entry.arguments)}
          </pre>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Device</label>
            <p className={`text-xs font-bold text-slate-300`}>
              {entry.device || 'Unknown'}
            </p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Auth Method</label>
            <p className="text-xs font-bold text-slate-300">
              {entry.auth_used ? 'Touch ID ✓' : entry.confirmed_verbally ? 'Verbal 💬' : 'None'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Duration</label>
            <p className="text-xs font-mono font-bold text-slate-300">{formatDuration(entry.duration_ms)}</p>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Timestamp</label>
            <p className="text-xs font-mono font-bold text-slate-300">{formatTimestamp(entry.timestamp)}</p>
          </div>
        </div>

        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 block mb-2">Status</label>
          <div className={`p-3 rounded-lg border text-xs font-bold flex items-center gap-2 ${entry.success ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-red-500/10 border-red-500/20 text-red-500'}`}>
            <span>{entry.success ? '✓ SUCCESS' : '🚫 BLOCKED'}</span>
            {!entry.success && entry.error && <span className="font-normal opacity-70"> — {entry.error}</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionDetail;
