import { useEffect } from 'react';

export function PostAuthPage({ result, onDismiss }) {
    const isApproved = result === 'approved';

    useEffect(() => {
        const id = setTimeout(onDismiss, 3000);
        return () => clearTimeout(id);
    }, [onDismiss]);

    return (
        <div className="bg-background-dark font-display antialiased flex flex-col min-h-screen relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center p-4 pt-6 justify-between shrink-0">
                <div
                    onClick={onDismiss}
                    className="text-slate-900 dark:text-slate-100 flex size-10 shrink-0 items-center justify-center rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                    <span className="material-symbols-outlined">arrow_back</span>
                </div>
                <h2 className="text-slate-900 dark:text-slate-100 text-base font-bold leading-tight tracking-tight flex-1 text-center pr-10 uppercase">Authorization Result</h2>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col items-center justify-center px-6">
                <div className="flex flex-col items-center gap-8 w-full animate-in zoom-in-95 duration-300">
                    {/* Status Icon */}
                    <div className={`flex items-center justify-center size-20 rounded-full border-2 ${isApproved ? 'border-sage/30 bg-sage/10' : 'border-muted-red/30 bg-muted-red/10'}`}>
                        <span className={`material-symbols-outlined ${isApproved ? 'text-sage' : 'text-muted-red'} text-5xl font-light`}>
                            {isApproved ? 'check_circle' : 'cancel'}
                        </span>
                    </div>

                    <div className="flex flex-col items-center gap-3">
                        <h1 className="text-slate-900 dark:text-slate-100 text-3xl font-extrabold tracking-tight text-center uppercase">
                            {isApproved ? 'Action Authorized' : 'Action Blocked'}
                        </h1>
                        <p className="font-mono text-slate-500 dark:text-slate-400 text-sm tracking-widest text-center uppercase font-bold">
                            {isApproved ? 'Executing on Mac' : 'Aegis halted execution'}
                        </p>
                    </div>

                    <button
                        onClick={onDismiss}
                        className="mt-4 text-primary dark:text-primary text-sm font-extrabold hover:underline decoration-2 underline-offset-4 uppercase tracking-widest"
                    >
                        Return to Monitor
                    </button>
                </div>
            </div>
        </div>
    );
}
