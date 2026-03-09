import React from 'react';

const Header = ({ status, isOffline, lastActive }) => {
  return (
    <header className="flex items-center justify-between px-8 py-4 border-b border-slate-200 dark:border-slate-800 bg-background-light dark:bg-background-dark sticky top-0 z-50 shrink-0 transition-colors duration-500">
      <div className="flex items-center gap-3">
        <div className="text-primary flex items-center justify-center">
          <span className="material-symbols-outlined text-3xl">shield</span>
        </div>
        <h1 className="text-xl font-black tracking-tight uppercase">Aegis</h1>
      </div>

      <div className="flex items-center gap-6">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-500 ${isOffline
            ? 'bg-amber-500/10 border-amber-500/20 text-amber-500'
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
          }`}>
          <span className="relative flex h-2 w-2">
            {!isOffline && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${isOffline ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
          </span>
          <span className="text-[10px] font-bold uppercase tracking-widest">
            {isOffline ? 'Agent Offline' : 'Agent Active'}
          </span>
        </div>

        <div className="h-8 w-px bg-slate-200 dark:border-slate-800"></div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              localStorage.removeItem('aegis_user_id');
              localStorage.removeItem('aegis_pin_verified');
              window.location.reload();
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-500 transition-all text-slate-500 group"
            title="Sign Out"
          >
            <span className="material-symbols-outlined text-lg">logout</span>
            <span className="text-[10px] font-bold uppercase tracking-widest hidden sm:inline">Sign Out</span>
          </button>
          <div className="h-8 w-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center overflow-hidden">
            <span className="material-symbols-outlined text-primary text-lg">person</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
