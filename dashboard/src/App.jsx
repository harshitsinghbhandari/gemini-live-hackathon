import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Header from './components/Header';
import StatsBar from './components/StatsBar';
import AuditLog from './components/AuditLog';
import ActionDetail from './components/ActionDetail';
import SetupPage from './pages/SetupPage';
import { useAuditLog } from './hooks/useAuditLog';
import { useAuditStream } from './hooks/useAuditStream';

const App = () => {
  const { initialLogs, loading, error: logError } = useAuditLog();
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

  const { status, error: streamError } = useAuditStream(onNewEntry);
  const isOffline = status === 'OFFLINE' || logError || streamError;

  const stats = useMemo(() => {
    return entries.reduce((acc, entry) => {
      acc.total++;
      if (entry.tier === 'GREEN') acc.green++;
      else if (entry.tier === 'YELLOW') acc.yellow++;
      else if (entry.tier === 'RED') acc.red++;
      if (entry.blocked) acc.blocked++;
      return acc;
    }, { total: 0, green: 0, yellow: 0, red: 0, blocked: 0 });
  }, [entries]);

  if (window.location.pathname === '/setup') {
    return <SetupPage />;
  }

  if (loading && entries.length === 0) {
    return (
      <div className="flex flex-col h-screen overflow-hidden text-slate-100 bg-background-dark font-display items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-500 font-mono text-xs uppercase tracking-widest">Loading secure logs...</p>
      </div>
    );
  }

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 antialiased min-h-screen font-display">
      <div className="max-w-[1440px] mx-auto flex flex-col min-h-screen">
        <Header status={status} isOffline={isOffline} lastActive={entries[0]?.timestamp} />

        <main className={`flex-1 p-8 space-y-8 transition-opacity duration-500 ${isOffline ? 'opacity-60 grayscale-[0.2]' : 'opacity-100'}`}>
          {isOffline && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-amber-500">cloud_off</span>
                <p className="text-amber-200 text-sm font-medium">Live feed paused. Showing last session data.</p>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="flex items-center gap-2 px-5 h-9 rounded-lg bg-primary text-white text-sm font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all uppercase tracking-widest"
              >
                <span className="material-symbols-outlined text-lg">refresh</span>
                Reconnect
              </button>
            </div>
          )}

          <StatsBar stats={stats} />

          <div className="flex flex-col lg:flex-row gap-6 items-start">
            <div className="w-full lg:w-[65%] bg-white dark:bg-slate-900/40 rounded border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xl">
              <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/20">
                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Audit Log</h3>
                <div className="flex gap-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-widest">
                    {entries.length} Entries
                  </span>
                </div>
              </div>
              <AuditLog
                entries={entries}
                onSelect={setSelectedEntry}
                selectedId={selectedEntry?.id}
              />
            </div>

            <div className="w-full lg:w-[35%] sticky top-24">
              <ActionDetail
                entry={selectedEntry}
                onClose={() => setSelectedEntry(null)}
              />
            </div>
          </div>
        </main>

        <footer className="px-8 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-bold">Aegis Core v2.4.0</p>
            <span className="text-slate-700 dark:text-slate-800 text-xs">|</span>
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-bold">Encrypted Connection</p>
          </div>
          <div className="flex gap-6">
            <a className="text-[10px] font-mono text-slate-500 hover:text-primary uppercase tracking-widest font-bold transition-colors" href="#">Docs</a>
            <a className="text-[10px] font-mono text-slate-500 hover:text-primary uppercase tracking-widest font-bold transition-colors" href="#">Support</a>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
