import React from 'react';

const TierBadge = ({ tier }) => {
  const getStyles = (tier) => {
    switch (tier?.toUpperCase()) {
      case 'GREEN': return 'bg-sage/10 text-sage border-sage/20';
      case 'YELLOW': return 'bg-amber/10 text-amber border-amber/20';
      case 'RED': return 'bg-crimson/10 text-crimson border-crimson/20';
      default: return 'bg-slate-600/10 text-slate-400 border-slate-600/20';
    }
  };

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-widest border transition-all duration-300 ${getStyles(tier)}`}>
      {tier || 'SILENT'}
    </span>
  );
};

export default TierBadge;
