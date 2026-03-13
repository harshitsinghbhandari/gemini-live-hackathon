// components/CountdownBar.jsx
// Shows a shrinking red progress bar over `total` seconds

export function CountdownBar({ total = 30, elapsed = 0 }) {
    const remaining = Math.max(0, total - elapsed);
    const pct = (remaining / total) * 100;
    return (
        <div className="countdown-wrapper">
            <div className="countdown-track">
                <div className="countdown-fill" style={{ width: `${pct}%` }} />
            </div>
            <span className="countdown-label">{remaining}s remaining</span>
        </div>
    );
}
