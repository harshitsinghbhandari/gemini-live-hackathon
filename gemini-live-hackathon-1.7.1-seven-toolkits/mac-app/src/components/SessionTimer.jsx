// components/SessionTimer.jsx
import { formatUptime } from '../utils/formatters.js';

export function SessionTimer({ seconds }) {
    return <span className="session-timer">{formatUptime(seconds)}</span>;
}
