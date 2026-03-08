import React, { useState } from 'react';

export function OnboardingPage({ onComplete }) {
    const [username, setUsername] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        const cleaned = username.trim().toLowerCase();
        if (cleaned) {
            localStorage.setItem("aegis_user_id", cleaned);
            onComplete(cleaned);
        }
    };

    return (
        <div className="bg-background-dark font-display antialiased flex flex-col min-h-screen items-center justify-center px-8 relative overflow-hidden">
            <div className="z-10 w-full max-w-sm flex flex-col items-center gap-8">
                {/* Shield Icon */}
                <div className="p-6 bg-primary/10 rounded-3xl animate-in zoom-in duration-500">
                    <span className="material-symbols-outlined !text-6xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
                        shield_person
                    </span>
                </div>

                <div className="text-center space-y-2">
                    <h1 className="text-3xl font-bold text-slate-100 uppercase tracking-tight">Configure Device</h1>
                    <p className="text-sm text-slate-400">Enter your Aegis username to bind this device.</p>
                </div>

                <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="aegis_username"
                        className="w-full bg-slate-800/50 border border-slate-700 text-slate-100 rounded-xl px-4 py-4 text-center font-mono placeholder:text-slate-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
                        autoCapitalize="none"
                        autoCorrect="off"
                        spellCheck="false"
                    />
                    <button
                        type="submit"
                        disabled={!username.trim()}
                        className="w-full py-4 mt-2 bg-primary hover:bg-primary-dark text-white rounded-xl font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
                    >
                        Bind to Agent
                    </button>
                </form>
            </div>

            {/* Background Decor */}
            <div className="absolute top-[-20%] left-[-20%] w-[140%] h-[60%] bg-primary/10 blur-[100px] rounded-full pointer-events-none"></div>
        </div>
    );
}
