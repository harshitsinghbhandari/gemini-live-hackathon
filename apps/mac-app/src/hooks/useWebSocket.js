// hooks/useWebSocket.js
// Connects to ws://localhost:8765, auto-reconnects every 3s
// Parses ALL events from aegis/ws_server.py

import { useState, useEffect, useRef, useCallback } from 'react';
import { CONFIG } from '../config.js';

const MAX_ACTIONS = 20;

export function useWebSocket() {
    const [isConnected, setIsConnected] = useState(false);
    const [status, setStatus] = useState('idle');        // idle | listening | executing | auth | blocked | error
    const [actions, setActions] = useState([]);
    const [pendingRed, setPendingRed] = useState(null);
    const [waveform, setWaveform] = useState(Array(20).fill(0.05));

    const wsRef = useRef(null);
    const reconnectTimer = useRef(null);
    const mountedRef = useRef(true);

    const connect = useCallback(() => {
        if (!mountedRef.current) return;
        try {
            const ws = new WebSocket(CONFIG.WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) return;
                setIsConnected(true);
                clearTimeout(reconnectTimer.current);
            };

            ws.onmessage = (ev) => {
                if (!mountedRef.current) return;
                try {
                    const msg = JSON.parse(ev.data);
                    const { event, value, data } = msg;

                    switch (event) {
                        case 'status':
                            setStatus(value || 'idle');
                            break;

                        case 'action':
                            if (data) {
                                setActions((prev) => {
                                    const next = [data, ...prev].slice(0, MAX_ACTIONS);
                                    return next;
                                });
                            }
                            break;

                        case 'red_auth_started':
                            setPendingRed(data || null);
                            break;

                        case 'red_auth_result':
                            // Clear pending red; the RedAuthPage polls backend again
                            // but we also surface the result here for immediate reaction
                            if (data?.approved != null) {
                                setPendingRed((prev) => prev ? { ...prev, _result: data.approved } : null);
                            }
                            break;

                        case 'session_started':
                            setActions([]);
                            setStatus('listening');
                            break;

                        case 'session_ended':
                            setStatus('idle');
                            setPendingRed(null);
                            break;

                        case 'waveform':
                            setWaveform((prev) => {
                                const next = [...prev.slice(1), value ?? 0.05];
                                return next;
                            });
                            break;

                        default:
                            break;
                    }
                } catch {
                    // ignore parse errors
                }
            };

            ws.onerror = () => { /* handled in onclose */ };

            ws.onclose = () => {
                if (!mountedRef.current) return;
                setIsConnected(false);
                wsRef.current = null;
                reconnectTimer.current = setTimeout(connect, 3000);
            };
        } catch {
            reconnectTimer.current = setTimeout(connect, 3000);
        }
    }, []);

    useEffect(() => {
        mountedRef.current = true;
        connect();
        return () => {
            mountedRef.current = false;
            clearTimeout(reconnectTimer.current);
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.close();
            }
        };
    }, [connect]);

    const sendMessage = useCallback((msg) => {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(msg));
        }
    }, []);

    return {
        isConnected,
        status,
        actions,
        pendingRed,
        waveform,
        sendMessage,
        clearPendingRed: () => setPendingRed(null),
        setActions,
    };
}
