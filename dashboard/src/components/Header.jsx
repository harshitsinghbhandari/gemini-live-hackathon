import React from 'react';

const Header = ({ status }) => {
  const isLive = status === 'LIVE';

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-purple-500/20 bg-background/50 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span className="text-xl">🛡️</span>
        <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-purple-400 bg-clip-text text-transparent">
          Guardian
        </h1>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-500 pulse-green' : 'bg-red-500'}`} />
        <span className={`text-[10px] font-bold tracking-[0.2em] ${isLive ? 'text-green-500' : 'text-red-500'}`}>
          {status}
        </span>
      </div>
    </header>
  );
};

export default Header;
