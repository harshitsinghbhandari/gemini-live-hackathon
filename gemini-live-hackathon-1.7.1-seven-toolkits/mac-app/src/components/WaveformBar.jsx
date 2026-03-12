// components/WaveformBar.jsx
import { useWaveform } from '../hooks/useWaveform.js';

export function WaveformBar({ values = [] }) {
    const heights = useWaveform(values);
    return (
        <div className="waveform-container">
            {heights.map((h, i) => (
                <div
                    key={i}
                    className="waveform-bar"
                    style={{ height: `${h}px` }}
                />
            ))}
        </div>
    );
}
