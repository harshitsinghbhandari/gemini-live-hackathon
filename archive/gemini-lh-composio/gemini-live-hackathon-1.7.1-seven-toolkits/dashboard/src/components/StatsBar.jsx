import React from 'react';

const StatCard = ({ label, value, colorClass }) => (
  <div className="flex-1 bg-white/5 border border-purple-500/10 p-4 rounded-xl backdrop-blur-sm">
    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">
      {label}
    </div>
    <div className={`text-2xl font-bold ${colorClass}`}>
      {value}
    </div>
  </div>
);

const StatsBar = ({ stats }) => {
  return (
    <div className="flex gap-4 p-6 border-b border-purple-500/10">
      <StatCard label="Total Actions" value={stats.total} colorClass="text-white" />
      <StatCard label="Green" value={stats.green} colorClass="text-green-500" />
      <StatCard label="Yellow" value={stats.yellow} colorClass="text-yellow-500" />
      <StatCard label="Red" value={stats.red} colorClass="text-red-500" />
      <StatCard label="Blocked" value={stats.blocked} colorClass="text-red-400" />
    </div>
  );
};

export default StatsBar;
