// components/TierBadge.jsx
import React from 'react';

export function TierBadge({ tier }) {
    if (!tier) return null;
    const upperTier = tier.toUpperCase();

    return (
        <div className={`tier-badge ${upperTier}`}>
            {upperTier}
        </div>
    );
}
