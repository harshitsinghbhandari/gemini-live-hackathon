import React from 'react';
import TierBadge from './TierBadge';
import { formatTimestamp, formatAction } from '../utils/formatters';

const AuditLog = ({ entries, onSelect, selectedId }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800/50 text-[10px] uppercase font-bold font-mono tracking-[0.2em] text-slate-500 border-b border-slate-200 dark:border-slate-800">
            <th className="px-6 py-4 font-medium">Action Description</th>
            <th className="px-6 py-4 font-medium">Timestamp</th>
            <th className="px-6 py-4 font-medium text-right">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
          {entries.map((entry, idx) => {
            const isSelected = selectedId === entry.id;
            const statusLabel = entry.blocked ? 'Blocked' : entry.auth_used ? 'Authorized' : entry.confirmed_verbally ? 'Confirmed' : 'Executed';
            const statusColor = entry.blocked ? 'text-crimson border-crimson/20 bg-crimson/10' : 'text-sage border-sage/20 bg-sage/10';

            return (
              <tr
                key={entry.id || idx}
                onClick={() => onSelect(entry)}
                className={`h-14 border-l-[6px] transition-all cursor-pointer group ${
                  entry.tier === 'RED' ? 'border-crimson' :
                  entry.tier === 'YELLOW' ? 'border-amber' :
                  'border-sage'
                } ${isSelected ? 'bg-slate-50 dark:bg-slate-800/40' : 'hover:bg-slate-50 dark:hover:bg-slate-800/20'}`}
              >
                <td className="px-6">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold uppercase tracking-tight text-slate-900 dark:text-slate-100 truncate max-w-md">
                      {formatAction(entry.action)}
                    </span>
                    <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mt-0.5">
                      {entry.tool || 'SYSTEM'} // {entry.toolkit || 'CORE'}
                    </span>
                  </div>
                </td>
                <td className="px-6 text-[11px] font-mono font-bold text-slate-500 uppercase">
                  {formatTimestamp(entry.timestamp)}
                </td>
                <td className="px-6 text-right">
                  <span className={`text-[10px] font-mono font-black uppercase py-1 px-2.5 rounded border tracking-widest ${statusColor}`}>
                    {statusLabel}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {entries.length === 0 && (
        <div className="p-12 flex flex-col items-center justify-center text-slate-500 gap-3 opacity-50">
          <span className="material-symbols-outlined text-4xl">inventory_2</span>
          <p className="text-xs font-bold uppercase tracking-[0.2em]">No audit logs found</p>
        </div>
      )}
    </div>
  );
};

export default AuditLog;
