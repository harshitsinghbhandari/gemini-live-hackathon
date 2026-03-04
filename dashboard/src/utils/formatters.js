export const formatTimestamp = (iso) => {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString('en-GB', { hour12: false });
};

export const formatDuration = (ms) => {
  if (ms === undefined || ms === null) return "0ms";
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
};

export const formatAction = (str) => {
  if (!str) return "";
  if (str.length > 40) {
    return str.substring(0, 37) + "...";
  }
  return str;
};

export const formatArguments = (obj) => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return "{}";
  }
};

export const getTierColor = (tier) => {
  switch (tier?.toUpperCase()) {
    case 'GREEN': return '#16a34a';
    case 'YELLOW': return '#ca8a04';
    case 'RED': return '#dc2626';
    default: return '#94a3b8';
  }
};

export const getToolkitName = (tool_slug) => {
  if (!tool_slug) return "";
  const parts = tool_slug.split('_');
  if (parts.length > 0) {
    return parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
  }
  return tool_slug;
};
