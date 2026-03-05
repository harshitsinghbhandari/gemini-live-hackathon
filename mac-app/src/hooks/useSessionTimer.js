// hooks/useSessionTimer.js
import { useState, useEffect, useRef } from 'react';

export function useSessionTimer(running) {
    const [seconds, setSeconds] = useState(0);
    const intervalRef = useRef(null);

    useEffect(() => {
        if (running) {
            setSeconds(0);
            intervalRef.current = setInterval(() => {
                setSeconds((s) => s + 1);
            }, 1000);
        } else {
            clearInterval(intervalRef.current);
        }
        return () => clearInterval(intervalRef.current);
    }, [running]);

    return seconds;
}
