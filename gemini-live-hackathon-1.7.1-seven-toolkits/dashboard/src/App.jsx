import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Header from './components/Header';
import AgentStatus from './components/AgentStatus';
import StatsBar from './components/StatsBar';
import AuditLog from './components/AuditLog';
import ActionDetail from './components/ActionDetail';
import { useAuditLog } from './hooks/useAuditLog';
import { useAuditStream } from './hooks/useAuditStream';

const App = () => {
  const { initialLogs, loading, error } = useAuditLog();
  const [entries, setEntries] = useState([]);
  const [selectedEntry, setSelectedEntry] = useState(null);

  useEffect(() => {
    if (initialLogs && initialLogs.length > 0) {
      setEntries(initialLogs);
    }
  }, [initialLogs]);

  const onNewEntry = useCallback((newEntry) => {
    setEntries(prev => {
      const exists = prev.some(e => (e.id && e.id === newEntry.id) || (e.timestamp === newEntry.timestamp && e.action === newEntry.action));
      if (exists) return prev;

      const updated = [newEntry, ...prev];
      return updated.slice(0, 100);
    });
  }, []);

  const { status } = useAuditStream(onNewEntry);

  const stats = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    const todayEntries = entries.filter(e => {
      if (!e.timestamp) return false;
      return e.timestamp.slice(0, 10) === today;
    });
    return todayEntries.reduce((acc, entry) => {
      acc.total++;
      if (entry.tier === 'GREEN') acc.green++;
      else if (entry.tier === 'YELLOW') acc.yellow++;
      else if (entry.tier === 'RED') acc.red++;
      if (entry.blocked) acc.blocked++;
      return acc;
    }, { total: 0, green: 0, yellow: 0, red: 0, blocked: 0 });
  }, [entries]);

  const lastEntry = entries[0];

  if (loading) {
    return (
      <div className="flex flex-col h-screen overflow-hidden text-slate-100 bg-background font-sans">
        <Header status="OFFLINE" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-slate-500 text-sm font-medium animate-pulse">Loading audit data…</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-screen overflow-hidden text-slate-100 bg-background font-sans">
        <Header status="OFFLINE" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-red-400 text-sm font-medium">Could not load audit history — {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden text-slate-100 bg-background font-sans">
      <Header status={status} />

      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 flex flex-col border-r border-purple-500/10 max-w-[calc(100vw-400px)]">
          <AgentStatus lastEntry={lastEntry} />
          <StatsBar stats={stats} />

          <div className="flex-1 flex flex-col min-h-0">
            <div className="px-6 py-4 flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                Live Audit Log
              </h2>
              {entries.length > 0 && (
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  {entries.length} Entries
                </span>
              )}
            </div>
            <AuditLog
              entries={entries}
              onSelect={setSelectedEntry}
              selectedId={selectedEntry?.id}
            />
          </div>
        </main>

        <aside className="w-[400px] flex-shrink-0 bg-background/50 backdrop-blur-sm">
          <ActionDetail
            entry={selectedEntry}
            onClose={() => setSelectedEntry(null)}
          />
        </aside>
      </div>
    </div>
  );
};

export default App;
