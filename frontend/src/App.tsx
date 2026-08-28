import { useCallback, useEffect, useState } from "react";
import { checkHealth, submitVerification, type BackendStatus } from "./api";
import { VerificationReport } from "./types";
import { UploadScreen } from "./components/UploadScreen";
import { ProcessingScreen } from "./components/ProcessingScreen";
import { ReportView } from "./components/ReportView";

type AppState = "upload" | "processing" | "report";

export default function App() {
  const [status, setStatus] = useState<BackendStatus>({ state: "checking" });
  const [appState, setAppState] = useState<AppState>("upload");
  const [report, setReport] = useState<VerificationReport | null>(null);

  const runCheck = useCallback((signal?: AbortSignal) => {
    setStatus({ state: "checking" });
    checkHealth(signal)
      .then((health) => setStatus({ state: "online", health }))
      .catch((err: unknown) => {
        if (signal?.aborted) return;
        const message = err instanceof Error ? err.message : "Unknown error";
        setStatus({ state: "offline", error: message });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    runCheck(controller.signal);
    return () => controller.abort();
  }, [runCheck]);

  const handleVerify = async (files: File[]) => {
    setAppState("processing");
    const result = await submitVerification(files);
    // Add artificial delay to let the processing animation finish its stages
    setTimeout(() => {
      setReport(result);
      setAppState("report");
    }, 6000); 
  };

  const handleReset = () => {
    setReport(null);
    setAppState("upload");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-8 h-8 text-guard-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <h1 className="text-xl font-bold tracking-tight text-guard-900">
              EvidenceGuard
            </h1>
          </div>
          <div className="flex items-center gap-3">
             <span className="text-sm text-slate-500 font-medium">Backend:</span>
             {status.state === "online" ? (
               <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700" title={`Connected to ${status.health.service} ${status.health.version}`}>
                 <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                 Online
               </span>
             ) : status.state === "offline" ? (
               <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-100 text-rose-700" title={status.error}>
                 <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                 Offline (Mock Mode)
               </span>
             ) : (
               <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                 <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                 Checking...
               </span>
             )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {appState === "upload" && <UploadScreen onVerify={handleVerify} />}
        {appState === "processing" && <ProcessingScreen />}
        {appState === "report" && report && <ReportView report={report} onReset={handleReset} />}
      </main>
    </div>
  );
}
