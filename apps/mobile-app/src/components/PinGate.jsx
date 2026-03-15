import React, { useState, useEffect } from 'react';

const PinGate = ({ children, backendUrl }) => {
    const [userId, setUserId] = useState('');
    const [pin, setPin] = useState('');
    const [isVerified, setIsVerified] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const savedUserId = localStorage.getItem('aegis_user_id');
        const verified = localStorage.getItem('aegis_pin_verified') === 'true';
        if (savedUserId && verified) {
            setIsVerified(true);
        }
        setLoading(false);
    }, []);

    const handleUnlock = async (e) => {
        e.preventDefault();
        if (!userId || !pin) return;

        setLoading(true);
        setError('');

        try {
            const res = await fetch(`${backendUrl}/auth/verify-pin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, pin })
            });

            if (res.ok) {
                localStorage.setItem('aegis_user_id', userId);
                localStorage.setItem('aegis_pin_verified', 'true');
                setIsVerified(true);
                window.location.reload();
            } else {
                setError('Invalid ID or PIN');
            }
        } catch (err) {
            console.error('Auth error:', err);
            setError('Connection error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    if (loading && !isVerified) {
        return (
            <div className="flex h-screen items-center justify-center bg-[#0a0a0f] text-slate-100">
                <div className="w-8 h-8 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
            </div>
        );
    }

    if (isVerified) {
        return children;
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-[#0a0a0f] font-sans antialiased px-6">
            <div className="w-full max-w-sm">
                <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                    {/* Accent Line */}
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-[#7c3aed]"></div>

                    <div className="flex flex-col items-center mb-8">
                        <div className="p-4 bg-[#7c3aed]/10 rounded-2xl mb-4 animate-in zoom-in duration-500">
                            <span className="material-symbols-outlined !text-4xl text-[#7c3aed]" style={{ fontVariationSettings: "'FILL' 1" }}>
                                shield_person
                            </span>
                        </div>
                        <h1 className="text-2xl font-bold text-white uppercase tracking-tight">◈ Aegis</h1>
                        <p className="text-slate-400 text-xs mt-1">Unlock Protected System</p>
                    </div>

                    <form onSubmit={handleUnlock} className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1">Aegis ID</label>
                            <input
                                type="text"
                                value={userId}
                                onChange={(e) => setUserId(e.target.value)}
                                placeholder="username"
                                className="w-full bg-slate-800/30 border border-slate-700 rounded-xl px-4 py-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#7c3aed]/50 transition-all font-mono text-center"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1">6-Digit PIN</label>
                            <input
                                type="password"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                value={pin}
                                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="••••••"
                                maxLength={6}
                                className="w-full bg-slate-800/30 border border-slate-700 rounded-xl px-4 py-4 text-white text-center tracking-[0.5em] text-2xl placeholder:text-slate-600 focus:outline-none focus:border-[#7c3aed]/50 transition-all font-mono"
                            />
                        </div>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-medium text-center py-3 rounded-xl animate-in shake duration-300">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading || userId.length < 3 || pin.length < 6}
                            className="w-full bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl uppercase tracking-widest text-sm shadow-lg shadow-[#7c3aed]/20 transition-all active:scale-[0.98] mt-4"
                        >
                            {loading ? 'Authenticating...' : 'Unlock Aegis'}
                        </button>
                    </form>
                </div>
 
                <p className="text-center text-slate-600 text-[10px] uppercase tracking-widest py-8 font-bold">
                    Aegis Core v2.4.0
                </p>
            </div>
        </div>
    );
};

export default PinGate;
