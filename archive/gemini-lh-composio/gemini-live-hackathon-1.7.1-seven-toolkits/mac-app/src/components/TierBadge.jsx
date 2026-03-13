// components/TierBadge.jsx
export function TierBadge({ tier }) {
    if (!tier) return null;
    const labels = { GREEN: '🟢 Green', YELLOW: '🟡 Yellow', RED: '🔴 Red' };
    return (
        <span className={`tier-badge ${tier}`}>
            {tier}
        </span>
    );
}
