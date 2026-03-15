import { useState, useEffect } from 'react';
import { CONFIG } from '../config.js';
import FaceIDButton from '../components/FaceIDButton.jsx';

export function RedAuthPage({ request, onResolve }) {
    const [seconds, setSeconds] = useState(30);

    useEffect(() => {
        // Sync to request creation time if available
        if (request.created_at) {
            const created = new Date(request.created_at).getTime();
            const now = Date.now();
            const diff = Math.floor((now - created) / 1000);
            setSeconds(Math.max(0, 30 - diff));
        }
    }, [request.created_at]);

    useEffect(() => {
        const id = setInterval(() => {
            setSeconds(s => {
                if (s <= 1) {
                    clearInterval(id);
                    handleDeny();
                    return 0;
                }
                return s - 1;
            });
        }, 1000);
        return () => clearInterval(id);
    }, []);

    async function handleDeny() {
        try {
            await fetch(`${CONFIG.BACKEND_URL}/auth/approve/${request.request_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-User-ID': CONFIG.USER_ID },
                body: JSON.stringify({ approved: false }),
            });
            onResolve('denied');
        } catch (err) {
            console.error('Deny failed:', err);
            onResolve('denied');
        }
    }

    const handleApproveSuccess = () => {
        onResolve('approved');
    };

    return (
        <div className="relative w-full h-full bg-background-dark overflow-hidden flex flex-col font-display">
            {/* Main Content Area */}
            <div className="flex-1 flex flex-col items-center justify-center px-6 relative">
                {/* Authorization Card */}
                <div className="w-full bg-card-dark border border-danger/20 rounded-xl p-6 shadow-2xl flex flex-col gap-6 animate-in slide-in-from-bottom-4 duration-300">
                    {/* Card Header */}
                    <div className="space-y-1">
                        <p className="text-slate-500 text-[10px] uppercase tracking-[0.2em] font-bold">Authorization Required</p>
                        <h1 className="text-xl font-bold leading-tight text-slate-100 uppercase tracking-tight">
                            {request.action}. This cannot be undone.
                        </h1>
                    </div>

                    {/* Visual Context — shows what the agent sees */}
                    <div className="w-full aspect-video rounded-lg overflow-hidden relative group bg-slate-800/50 flex items-center justify-center border-2 border-danger/30">
                        <div className="absolute inset-0 bg-gradient-to-br from-danger/10 to-transparent mix-blend-overlay"></div>
                        {request.visual_context?.base64_image ? (
                            <img
                                className="w-full h-full object-contain"
                                alt="What Aegis sees right now"
                                src={`data:${request.visual_context.mime_type || 'image/jpeg'};base64,${request.visual_context.base64_image}`}
                            />
                        ) : (
                            <img
                                className="w-full h-full object-cover opacity-60"
                                alt="Security Context"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD4GmpBd3LHtpS-TJL2SZIH4pVUtA030fgVYpxnQ5U9qEitZo3iPKceU8jcwRQtOqG9-vmamcGDISWxXn9i9rVEFDD9uX3N2knRl1wQp0qpcwb0QqNzFPpSATxpKpXrQqWNJ3FXdjjbThehRJgkhC8r4pv2qYrv5I8HVjCDx_Mk9DyOsvgtzTVbRW0qdQk7ySuzRm2Mlcvo_-FlD2adiUuzuCwW7h9lQygHMDZ3yNGfFlVFnDlQPtxlbzfJTvg2n4gm-s431DLGmyZ-"
                            />
                        )}
                        <div className="absolute top-2 left-2 bg-danger/80 text-white text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded">
                            {request.visual_context?.base64_image ? 'LIVE AGENT VIEW' : 'NO VISUAL'}
                        </div>
                        {!request.visual_context?.base64_image && (
                            <div className="absolute inset-0 flex items-center justify-center">
                                <span className="material-symbols-outlined text-4xl text-danger/50 animate-pulse">lock</span>
                            </div>
                        )}
                    </div>

                    {/* Timer Section */}
                    <div className="flex flex-col items-center gap-2 py-2">
                        <div className="flex gap-3 font-mono">
                            <div className="flex flex-col items-center">
                                <div className="bg-slate-800/50 w-20 h-20 rounded-2xl flex items-center justify-center text-4xl font-black text-danger border border-danger/10 shadow-inner">
                                    {seconds.toString().padStart(2, '0')}
                                </div>
                                <span className="text-[10px] text-slate-500 mt-2 uppercase tracking-widest font-bold">Seconds remaining</span>
                            </div>
                        </div>
                    </div>

                    {/* Reasoning Detail */}
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                        <p className="font-mono text-[11px] text-slate-400 break-all leading-relaxed uppercase">
                            REASON: {request.reason} <br />
                            <span className="text-slate-500 text-[10px] uppercase font-bold tracking-widest">({request.tool || 'SYSTEM_ACTION'})</span>
                        </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-3 pt-2">
                        <FaceIDButton
                            requestId={request.request_id}
                            onApprove={handleApproveSuccess}
                            onDeny={handleDeny}
                        />
                        <button
                            onClick={handleDeny}
                            className="bg-transparent hover:bg-white/5 text-slate-400 font-bold py-2 rounded-lg transition-colors text-xs uppercase tracking-widest"
                        >
                            Deny Request
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
