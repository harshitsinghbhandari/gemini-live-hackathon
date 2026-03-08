import React from 'react';
import TierBadge from './TierBadge';
import { formatTimestamp, formatDuration, formatArguments } from '../utils/formatters';

const ActionDetail = ({ entry, onClose }) => {
  if (!entry) {
    return (
      <div className="bg-white dark:bg-slate-900/40 rounded border border-slate-200 dark:border-slate-800 h-[600px] flex flex-col items-center justify-center p-12 text-center shadow-xl">
        <div className="mb-6 h-16 w-16 rounded-full border border-dashed border-slate-300 dark:border-slate-700 flex items-center justify-center">
          <span className="material-symbols-outlined text-slate-300 dark:text-slate-700 text-3xl">data_exploration</span>
        </div>
        <h4 className="text-slate-900 dark:text-slate-100 font-black uppercase tracking-widest mb-2">Inspect Audit Event</h4>
        <p className="text-slate-500 text-[11px] font-bold uppercase tracking-widest max-w-[240px]">Select an action from the audit log to inspect detailed metadata and trace logs.</p>
        <div className="mt-8 w-full space-y-3 opacity-10 pointer-events-none">
          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-3/4 mx-auto"></div>
          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/2 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#101822] rounded border border-slate-200 dark:border-slate-800 h-[800px] flex flex-col shadow-2xl animate-in slide-in-from-right-4 duration-300">
      {/* Detail Header */}
      <div className="px-6 py-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131b26]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Incident Detail</span>
            <TierBadge tier={entry.tier} />
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 transition-colors">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-50 uppercase leading-tight">
          {entry.action}
        </h1>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400 leading-relaxed font-bold uppercase tracking-tight italic opacity-80">
          Reason: {entry.reason || 'Standard policy assessment applied during execution flow.'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-x-8 gap-y-6">
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Risk Classification</span>
            <div className="font-mono text-[11px] font-bold text-slate-900 dark:text-slate-100 border-l-2 border-primary pl-3 py-0.5 uppercase">
              {entry.tier}_SECURITY_POLICY
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Auth Device</span>
            <div className="font-mono text-[11px] font-bold text-slate-900 dark:text-slate-100 border-l-2 border-slate-300 dark:border-slate-700 pl-3 py-0.5 uppercase">
              {entry.device || 'LOCAL_MAC_AGENT'}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Outcome</span>
            <div className={`font-mono text-[11px] font-black border-l-2 pl-3 py-0.5 uppercase ${entry.success ? 'text-sage border-sage' : 'text-crimson border-crimson'}`}>
              {entry.blocked ? 'BLOCKED_BY_POLICY' : entry.success ? 'EXECUTED_SUCCESS' : 'FAILED_ERROR'}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Duration</span>
            <div className="font-mono text-[11px] font-bold text-slate-900 dark:text-slate-100 border-l-2 border-slate-300 dark:border-slate-700 pl-3 py-0.5 uppercase">
              {formatDuration(entry.duration_ms)}
            </div>
          </div>
        </div>

        {/* Arguments */}
        <div className="flex flex-col gap-3">
          <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Arguments Trace</span>
          <pre className="text-[11px] font-mono font-bold bg-slate-100 dark:bg-black/40 p-4 rounded-lg border border-slate-200 dark:border-slate-800 overflow-x-auto text-primary leading-relaxed">
            {formatArguments(entry.arguments)}
          </pre>
        </div>

        {/* Timestamp Chain */}
        <div className="flex flex-col gap-3 pt-2">
          <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Security Lifecycle</span>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="font-mono text-[10px] font-bold text-slate-500 w-36 shrink-0 uppercase">{formatTimestamp(entry.timestamp)}</div>
              <div className="h-px grow bg-slate-200 dark:bg-slate-800"></div>
              <div className="font-mono text-[10px] font-black text-slate-700 dark:text-slate-300 italic uppercase">Log_Captured</div>
            </div>
            {entry.auth_used && (
              <div className="flex items-center gap-3">
                <div className="font-mono text-[10px] font-bold text-slate-500 w-36 shrink-0 uppercase">{formatTimestamp(entry.timestamp)}</div>
                <div className="h-px grow bg-primary/20"></div>
                <div className="font-mono text-[10px] font-black text-primary italic uppercase">Biometric_Verified</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="mt-auto p-6 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-3">
        <button className="w-full py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-900 dark:text-slate-100 text-xs font-black uppercase tracking-widest rounded transition-all flex items-center justify-center gap-2 border border-slate-200 dark:border-slate-700">
          <span className="material-symbols-outlined text-sm">terminal</span>
          Export Entry (JSON)
        </button>
      </div>
    </div>
  );
};

export default ActionDetail;
