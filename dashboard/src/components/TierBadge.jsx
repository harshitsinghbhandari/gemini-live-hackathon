import React from 'react';

const TierBadge = ({ tier }) => {
  const getStyles = (tier) => {
    switch (tier?.toUpperCase()) {
      case 'GREEN': return 'bg-[#16a34a] text-white';
      case 'YELLOW': return 'bg-[#ca8a04] text-white';
      case 'RED': return 'bg-[#dc2626] text-white';
      default: return 'bg-gray-600 text-white';
    }
  };

  const getEmoji = (tier) => {
    switch (tier?.toUpperCase()) {
      case 'GREEN': return '🟢';
      case 'YELLOW': return '🟡';
      case 'RED': return '🔴';
      default: return '⚪';
    }
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${getStyles(tier)}`}>
      <span className="text-[8px]">{getEmoji(tier)}</span>
      {tier}
    </span>
  );
};

export default TierBadge;
