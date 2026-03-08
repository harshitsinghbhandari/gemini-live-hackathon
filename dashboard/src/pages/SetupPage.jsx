import React, { useState } from 'react';

const SetupPage = () => {
    const [step, setStep] = useState(1);
    const [formData, setFormData] = useState({
        username: '',
        googleApiKey: '',
        composioApiKey: ''
    });

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value.trim() });
    };

    const isStep1Valid = formData.username && formData.googleApiKey && formData.composioApiKey;

    const generateEnvContent = () => {
        return `GOOGLE_API_KEY=${formData.googleApiKey}
COMPOSIO_API_KEY=${formData.composioApiKey}
USER_ID=${formData.username}
`;
    };

    const handleDownloadEnv = () => {
        const element = document.createElement("a");
        const file = new Blob([generateEnvContent()], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = ".env";
        document.body.appendChild(element); // Required for this to work in FireFox
        element.click();
    };

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 font-display flex flex-col items-center py-12 px-6">

            <div className="w-full max-w-2xl mb-8 flex items-center gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
                <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined !text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>person_add</span>
                </div>
                <div>
                    <h1 className="text-2xl font-bold uppercase tracking-tight">Setup New Agent</h1>
                    <p className="text-sm text-slate-500 font-mono tracking-widest uppercase mt-1">Configure your personal Aegis instance</p>
                </div>
            </div>

            <div className="w-full max-w-2xl bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">

                {/* Progress Bar Header */}
                <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                    {[1, 2, 3, 4].map(s => (
                        <div key={s} className={`flex-1 py-4 text-center border-b-2 transition-colors ${step === s ? 'border-primary text-primary' : (step > s ? 'border-emerald-500 text-emerald-500' : 'border-transparent text-slate-400')}`}>
                            <span className="text-xs font-bold uppercase tracking-widest">
                                {s === 1 ? 'Keys' : s === 2 ? 'Tools' : s === 3 ? 'Install' : 'Done'}
                            </span>
                        </div>
                    ))}
                </div>

                <div className="p-8">
                    {/* STEP 1 */}
                    {step === 1 && (
                        <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Username (Required)</label>
                                    <input type="text" name="username" value={formData.username} onChange={handleChange} placeholder="e.g. harshitbhandari" className="w-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 font-mono text-sm focus:outline-none focus:border-primary/50 transition-colors" />
                                    <p className="mt-2 text-[10px] text-slate-400">Used for identifying your devices and logs.</p>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Google Gemini API Key</label>
                                    <input type="password" name="googleApiKey" value={formData.googleApiKey} onChange={handleChange} placeholder="AIzaSy..." className="w-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 font-mono text-sm focus:outline-none focus:border-primary/50 transition-colors" />
                                </div>

                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Composio API Key</label>
                                    <input type="password" name="composioApiKey" value={formData.composioApiKey} onChange={handleChange} placeholder="...key..." className="w-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 font-mono text-sm focus:outline-none focus:border-primary/50 transition-colors" />
                                </div>
                            </div>

                            <button
                                onClick={() => setStep(2)}
                                disabled={!isStep1Valid}
                                className="w-full py-4 mt-4 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold uppercase tracking-widest disabled:opacity-50 transition-all shadow-lg"
                            >
                                Continue to Connections
                            </button>
                        </div>
                    )}

                    {/* STEP 2 */}
                    {step === 2 && (
                        <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                            <div className="p-6 bg-slate-100 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/50 rounded-xl">
                                <h3 className="text-sm font-bold uppercase tracking-widest mb-4 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-primary">link</span>
                                    Connect Toolkits
                                </h3>
                                <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
                                    Before starting your agent, you need to connect your accounts on Composio. Aegis requires the following toolkits to be active:
                                </p>
                                <ul className="space-y-3 font-mono text-xs text-slate-600 dark:text-slate-300">
                                    <li className="flex items-center gap-2">✓ <span className="text-white">Gmail</span></li>
                                    <li className="flex items-center gap-2">✓ <span className="text-white">Google Calendar</span></li>
                                    <li className="flex items-center gap-2">✓ <span className="text-white">Google Docs / Sheets / Slides</span></li>
                                    <li className="flex items-center gap-2">✓ <span className="text-white">GitHub</span></li>
                                </ul>
                                <div className="mt-8 flex justify-center">
                                    <a href="https://app.composio.dev/app/integrations" target="_blank" rel="noreferrer" className="px-6 py-3 bg-[#1B1B1F] text-white rounded-lg font-bold text-xs uppercase tracking-widest border border-slate-700 hover:bg-[#2A2A2F] transition-colors flex items-center gap-2">
                                        Open Composio Dashboard
                                        <span className="material-symbols-outlined text-sm">open_in_new</span>
                                    </a>
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button onClick={() => setStep(1)} className="w-1/3 py-4 rounded-xl font-bold uppercase tracking-widest text-slate-500 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                                    Back
                                </button>
                                <button onClick={() => setStep(3)} className="w-2/3 py-4 bg-primary text-white rounded-xl font-bold uppercase tracking-widest shadow-lg hover:bg-primary/90 transition-all">
                                    I've connected my tools
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 3 */}
                    {step === 3 && (
                        <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                            <div className="p-6 border border-emerald-500/30 bg-emerald-500/5 rounded-xl text-center">
                                <span className="material-symbols-outlined text-5xl text-emerald-500 mb-4">download</span>
                                <h3 className="text-lg font-bold uppercase tracking-tight text-emerald-500 mb-2">Your Profile is Ready</h3>
                                <p className="text-sm text-slate-400 mb-6">Download your environment file containing your secure keys.</p>
                                <button onClick={handleDownloadEnv} className="px-8 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-bold text-sm uppercase tracking-widest shadow-lg shadow-emerald-500/20 transition-all">
                                    Download .env
                                </button>
                            </div>

                            <div className="p-6 bg-slate-100 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/50 rounded-xl">
                                <h4 className="text-xs font-bold uppercase tracking-widest mb-4">Installation</h4>
                                <p className="text-xs text-slate-500 mb-4">Open Terminal on your Mac and run this command from your Downloads directory:</p>
                                <div className="bg-black/50 p-4 rounded-lg border border-slate-700 font-mono text-xs text-emerald-400 overflow-x-auto">
                                    curl -s https://aegis.projectalpha.in/install.sh | bash
                                </div>
                                <p className="text-[10px] text-slate-500 mt-4 italic">Note: Make sure your downloaded .env is in the same folder where you run this command.</p>
                            </div>

                            <div className="flex gap-4">
                                <button onClick={() => setStep(2)} className="w-1/3 py-4 rounded-xl font-bold uppercase tracking-widest text-slate-500 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                                    Back
                                </button>
                                <button onClick={() => setStep(4)} className="w-2/3 py-4 bg-primary text-white rounded-xl font-bold uppercase tracking-widest shadow-lg hover:bg-primary/90 transition-all">
                                    Continue
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 4 */}
                    {step === 4 && (
                        <div className="text-center space-y-8 animate-in slide-in-from-right-4 duration-300 py-4">
                            <div className="w-24 h-24 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="material-symbols-outlined text-5xl text-emerald-500" style={{ fontVariationSettings: "'FILL' 1" }}>task_alt</span>
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold uppercase tracking-tight text-slate-100 mb-2">You're All Set!</h2>
                                <p className="text-sm text-slate-400">Your agent is configured and ready to protect.</p>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
                                <a href="/" className="p-6 border border-slate-700 rounded-xl hover:bg-slate-800/50 transition-colors flex flex-col items-center gap-3">
                                    <span className="material-symbols-outlined text-primary text-3xl">monitoring</span>
                                    <span className="text-xs font-bold uppercase tracking-widest">Open DB Dashboard</span>
                                </a>
                                <a href="https://aegismobile.projectalpha.in" target="_blank" rel="noreferrer" className="p-6 border border-slate-700 rounded-xl hover:bg-slate-800/50 transition-colors flex flex-col items-center gap-3">
                                    <span className="material-symbols-outlined text-accent-red text-3xl">phone_iphone</span>
                                    <span className="text-xs font-bold uppercase tracking-widest">Open Mobile App</span>
                                </a>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SetupPage;
