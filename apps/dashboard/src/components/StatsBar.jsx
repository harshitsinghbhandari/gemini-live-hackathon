import React from 'react';

const StatCard = ({ label, value, colorClass, borderClass }) => (
  <div className={`bg-white dark:bg-slate-900/40 p-5 border-t-2 rounded shadow-sm transition-all duration-300 ${borderClass}`}>
    <p className="text-[10px] font-mono font-bold text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] mb-2">{label}</p>
    <p className={`text-3xl font-display font-extrabold ${colorClass}`}>{value}</p>
  </div>
);

const StatsBar = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard label="Total Actions" value={stats.total} colorClass="dark:text-slate-100" borderClass="border-primary" />
      <StatCard label="Authorized" value={stats.green + stats.yellow + stats.red - stats.blocked} colorClass="text-sage" borderClass="border-sage" />
      <StatCard label="Flagged" value={stats.yellow} colorClass="text-amber" borderClass="border-amber" />
      <StatCard label="Blocked" value={stats.blocked} colorClass="text-crimson" borderClass="border-crimson" />
    </div>
  );
};

export default StatsBar;
