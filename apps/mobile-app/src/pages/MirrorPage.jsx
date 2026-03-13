import React, { useState, useEffect } from 'react';
import { useAuditMirror } from '../hooks/useAuditMirror.js';
import { ActionCard } from '../components/ActionCard.jsx';
import { CONFIG } from '../config.js';
import { registerFaceID } from '../components/FaceIDButton.jsx';

export function MirrorPage({ onStopSession }) {
    const logs = useAuditMirror();
    const isActive = logs.length > 0; // Simplified active check based on logs
    const [faceIDRegistered, setFaceIDRegistered] = useState(true);

    useEffect(() => {
        // Check if Face ID is registered
        fetch(`${CONFIG.BACKEND_URL}/webauthn/registered/${CONFIG.USER_ID}`, { headers: { 'X-User-ID': CONFIG.USER_ID } })
            .then(r => r.json())
            .then(data => setFaceIDRegistered(data.registered))
            .catch(() => { });
    }, []);

    const handleSetupFaceID = async () => {
        try {
            const success = await registerFaceID();
            if (success) {
                setFaceIDRegistered(true);
            }
        } catch (e) {
            console.error("Setup failed", e);
        }
    };

    const handleStop = async () => {
        if (!confirm('Stop Mac session?')) return;
        try {
            await fetch(`${CONFIG.BACKEND_URL}/session/stop`, { method: 'POST', headers: { 'X-User-ID': CONFIG.USER_ID } });
            if (onStopSession) onStopSession();
        } catch (e) {
            console.error('Failed to stop session', e);
        }
    };

    return (
        <div className="bg-background-dark font-display antialiased flex flex-col min-h-screen relative overflow-hidden">
            {/* Status Bar */}
            <div className="h-12 w-full flex items-center justify-between px-8 pt-4 shrink-0">
                <span className="text-slate-100 text-sm font-semibold">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}</span>
                <button
                    onClick={() => {
                        localStorage.removeItem('aegis_user_id');
                        localStorage.removeItem('aegis_pin_verified');
                        window.location.reload();
                    }}
                    className="p-2 rounded-full bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-red-400 transition-colors"
                >
                    <span className="material-symbols-outlined text-xl">logout</span>
                </button>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col items-center justify-center px-8">
                {/* Aegis Shield Icon */}
                <div className="mb-8 p-6 bg-primary/10 rounded-3xl">
                    <div className="text-primary flex items-center justify-center">
                        <span className="material-symbols-outlined !text-6xl" style={{ fontVariationSettings: "'FILL' 1, 'wght' 300" }}>shield_with_heart</span>
                    </div>
                </div>

                {/* Title */}
                <h1 className="text-slate-100 text-2xl font-medium tracking-tight mb-12">Aegis Mobile</h1>

                {/* Connection Status */}
                <div className="flex flex-col items-center gap-4 w-full">
                    <div className="flex items-center gap-3 px-5 py-2.5 bg-slate-800/40 rounded-full border border-slate-700/50">
                        <span className="relative flex h-2.5 w-2.5">
                            {isActive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isActive ? 'bg-emerald-500' : 'bg-slate-500'}`}></span>
                        </span>
                        <span className="text-slate-100 text-sm font-medium">{isActive ? 'Session Active' : 'Waiting for Session'}</span>
                    </div>
                    <p className="font-mono text-slate-500 text-xs tracking-widest uppercase">{CONFIG.DEVICE_ID}</p>
                </div>

                {/* Face ID Setup Prompt */}
                {!faceIDRegistered && (
                    <div className="mt-8 w-full p-4 rounded-xl bg-primary/10 border border-primary/20 flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <p className="text-xs font-bold text-primary uppercase tracking-widest leading-relaxed">
                            Biometric authentication not configured for this device.
                        </p>
                        <button
                            onClick={handleSetupFaceID}
                            className="bg-primary text-white text-xs font-black py-2 rounded-lg uppercase tracking-widest shadow-lg shadow-primary/20 transition-all hover:scale-[1.02]"
                        >
                            Setup Face ID
                        </button>
                    </div>
                )}
            </div>

            {/* Bottom Actions */}
            <div className="p-8 pb-12 flex flex-col items-center gap-6 shrink-0">
                <button
                    onClick={handleStop}
                    className="w-full py-4 rounded-xl border border-red-500/40 text-red-500 font-bold text-base hover:bg-red-500/5 transition-colors uppercase tracking-widest"
                >
                    Stop Session
                </button>
                {/* Home Indicator */}
                <div className="w-32 h-1.5 bg-slate-700 rounded-full mt-2"></div>
            </div>

            {/* Background Subtle Gradient Decor */}
            <div className="absolute top-[-10%] left-[-10%] w-[120%] h-[40%] bg-primary/5 blur-[120px] rounded-full pointer-events-none"></div>
        </div>
    );
}
