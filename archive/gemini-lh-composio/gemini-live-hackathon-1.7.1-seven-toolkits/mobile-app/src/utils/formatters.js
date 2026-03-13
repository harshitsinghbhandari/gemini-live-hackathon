// src/utils/formatters.js

export function formatDuration(ms) {
    if (ms == null) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

export function formatTimestamp(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function toolkitLabel(toolkit) {
    if (!toolkit) return 'unknown';
    return toolkit.charAt(0).toUpperCase() + toolkit.slice(1);
}
