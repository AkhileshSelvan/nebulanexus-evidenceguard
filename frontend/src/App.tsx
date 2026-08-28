import { useCallback, useEffect, useRef, useState } from "react";
import { checkHealth, verifyBundle, type BackendStatus } from "./api";
import type { VerificationReport } from "./types";
import { UploadScreen } from "./components/UploadScreen";
import { ProcessingScreen } from "./components/ProcessingScreen";
import { ReportView } from "./components/ReportView";

type AppState =
  | { screen: "upload" }
  | { screen: "processing"; fileCount: number }
  | { screen: "report"; report: VerificationReport }
  // Honest failure state: a failed /verify call NEVER falls back to
  // fabricated evidence -- the reviewer sees the real error and can retry.
  | { screen: "error"; message: string };

function StatusPill({ status, onRetry }: { status: BackendStatus; onRetry: () => void }) {
  if (status.state === "online") {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200"
        title={`Connected to ${status.health.service} ${status.health.version}`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
        Connected
      </span>
    );
  }
  if (status.state === "offline") {
    return (
      <button
        type="button"
        onClick={onRetry}
        className="eg-press inline-flex min-h-[32px] items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-200 hover:bg-rose-100"
        title={status.error}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-rose-500" aria-hidden="true" />
        Offline · retry
      </button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" aria-hidden="true" />
      Checking
    </span>
  );
}

export default function App() {
  const [status, setStatus] = useState<BackendStatus>({ state: "checking" });
  const [appState, setAppState] = useState<AppState>({ screen: "upload" });
  const mainRef = useRef<HTMLElement>(null);

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

  /* On screen change, move focus to the main region so keyboard and screen
     reader users land on the new content rather than the top of the document. */
  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
  }, [appState.screen]);

  const handleVerify = async (files: File[]) => {
    setAppState({ screen: "processing", fileCount: files.length });
    try {
      const report = await verifyBundle(files);
      setAppState({ screen: "report", report });
    } catch (err) {
      setAppState({
        screen: "error",
        message:
          err instanceof Error
            ? err.message
            : "The backend did not return a verification report.",
      });
    }
  };

  const handleReset = () => setAppState({ screen: "upload" });

  return (
    <div className="min-h-dvh bg-slate-50 font-sans text-slate-900">
      <a
        href="#main"
        className="skip-link rounded-lg bg-guard-700 px-3 py-2 text-sm font-medium text-white shadow-lg"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-guard-600 text-white"
              aria-hidden="true"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-base font-bold leading-tight tracking-tight text-slate-900">
                EvidenceGuard
              </h1>
              <p className="hidden truncate text-[11px] leading-tight text-slate-500 sm:block">
                Verify the evidence, not just the document
              </p>
            </div>
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            <span className="hidden text-xs font-medium text-slate-500 sm:inline">Backend</span>
            <StatusPill status={status} onRetry={() => runCheck()} />
          </div>
        </div>
      </header>

      <main
        id="main"
        ref={mainRef}
        tabIndex={-1}
        className="mx-auto max-w-7xl px-4 py-6 outline-none sm:px-6 sm:py-8 lg:px-8"
      >
        {appState.screen === "upload" && <UploadScreen onVerify={handleVerify} />}

        {appState.screen === "processing" && <ProcessingScreen fileCount={appState.fileCount} />}

        {appState.screen === "report" && (
          <ReportView report={appState.report} onReset={handleReset} />
        )}

        {appState.screen === "error" && (
          <div className="eg-scale-in mx-auto max-w-lg py-16 text-center" role="alert">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-100">
              <svg
                className="h-6 w-6 text-rose-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Verification failed</h2>
            <p className="mb-2 text-sm text-slate-600">{appState.message}</p>
            <p className="mx-auto mb-6 max-w-sm text-xs leading-relaxed text-slate-500">
              No result is shown because none was produced. EvidenceGuard never substitutes
              placeholder findings for a failed analysis.
            </p>
            <button
              type="button"
              onClick={handleReset}
              className="eg-press inline-flex min-h-[44px] items-center rounded-lg bg-guard-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-guard-700"
            >
              Try again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
