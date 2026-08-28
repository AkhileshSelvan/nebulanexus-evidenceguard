import { useCallback, useEffect, useState } from "react";

import { checkHealth, type BackendStatus } from "./api";

export default function App() {
  const [status, setStatus] = useState<BackendStatus>({ state: "checking" });

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

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-8 px-6 py-16">
        <header className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-guard-900">
            EvidenceGuard
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Verify the evidence, not just the document.
          </p>
        </header>

        <ConnectionCard status={status} onRetry={() => runCheck()} />

        <footer className="text-xs text-slate-400">
          OBLIVION 2026 · foundation build
        </footer>
      </div>
    </div>
  );
}

function ConnectionCard({
  status,
  onRetry,
}: {
  status: BackendStatus;
  onRetry: () => void;
}) {
  const meta = {
    checking: { dot: "bg-amber-400", label: "Checking backend…" },
    online: { dot: "bg-emerald-500", label: "Backend connected" },
    offline: { dot: "bg-rose-500", label: "Backend offline" },
  }[status.state];

  return (
    <section className="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span className={`h-3 w-3 rounded-full ${meta.dot}`} aria-hidden />
        <span className="font-medium">{meta.label}</span>
        <button
          type="button"
          onClick={onRetry}
          className="ml-auto rounded-md border border-slate-200 px-3 py-1 text-sm text-slate-600 transition hover:bg-slate-50"
        >
          Re-check
        </button>
      </div>

      <dl className="mt-4 space-y-1 text-sm text-slate-600">
        {status.state === "online" && (
          <>
            <Row label="Service" value={status.health.service} />
            <Row label="Version" value={status.health.version} />
            <Row label="Server time" value={status.health.time} />
          </>
        )}
        {status.state === "offline" && (
          <p className="text-slate-500">
            Could not reach <code>/health</code> ({status.error}). Start the
            backend with{" "}
            <code className="rounded bg-slate-100 px-1">
              uvicorn app.main:app --port 8000
            </code>
            .
          </p>
        )}
        {status.state === "checking" && (
          <p className="text-slate-500">Contacting the API…</p>
        )}
      </dl>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-400">{label}</dt>
      <dd className="font-mono text-slate-700">{value}</dd>
    </div>
  );
}
