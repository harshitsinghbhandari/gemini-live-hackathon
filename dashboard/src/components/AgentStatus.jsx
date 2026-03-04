import React from 'react';

const AgentStatus = ({ lastEntry }) => {
  const getAgentStatusText = () => {
    if (!lastEntry) return "Listening";
    if (lastEntry.blocked) return "Waiting for input";
    if (lastEntry.auth_used && lastEntry.status === 'pending') return "Waiting for auth";
    if (lastEntry.success) return "Listening";
    return "Executing";
  };

  const getStatusDotColor = () => {
    const status = getAgentStatusText();
    switch (status) {
      case "Listening": return "bg-green-500 pulse-green";
      case "Executing": return "bg-orange-500";
      case "Waiting for auth": return "bg-red-500 animate-pulse";
      default: return "bg-green-500 pulse-green";
    }
  };

  return (
    <div className="flex flex-col gap-2 p-6 border-b border-purple-500/10">
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${getStatusDotColor()}`} />
        <h2 className="text-xl font-bold">{getAgentStatusText()}</h2>
      </div>
      <div className="flex flex-col">
        <p className="text-sm text-slate-400 font-medium tracking-tight">
          Harshit's MacBook
        </p>
      </div>
    </div>
  );
};

export default AgentStatus;
