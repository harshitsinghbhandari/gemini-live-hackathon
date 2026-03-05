// hooks/useWaveform.js
// Smooths raw waveform amplitudes into display heights (px)

import { useMemo } from 'react';

const MIN_HEIGHT = 4;
const MAX_HEIGHT = 60;

export function useWaveform(rawValues = []) {
    const heights = useMemo(() => {
        return rawValues.map((v) => {
            const clamped = Math.min(Math.max(v, 0), 1);
            return Math.round(MIN_HEIGHT + clamped * (MAX_HEIGHT - MIN_HEIGHT));
        });
    }, [rawValues]);

    return heights;
}
