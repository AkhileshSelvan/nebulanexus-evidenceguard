import { useElapsedSeconds, stagger } from "../motion";

/**
 * Shown while POST /api/v1/verify is in flight.
 *
 * HONESTY NOTE — this screen deliberately does NOT claim per-stage progress.
 * `/verify` is a single blocking request that returns only once the whole
 * pipeline has finished; it streams no stage events. An earlier version
 * advanced these stages on hardcoded timers (800ms, 1500ms, …), which reached
 * "complete" while the backend was still working — a 9-document bundle takes
 * 60-90s. That was fabricated progress.
 *
 * So the stages below are a *map of what runs*, not a progress bar. The only
 * moving parts are an indeterminate bar (means "working", claims no
 * percentage) and a real elapsed clock.
 */

const PIPELINE = [
  { id: "ingest", label: "Ingest", detail: "Hash, size and type per document" },
  { id: "ocr", label: "OCR", detail: "Local Tesseract text + field extraction" },
  { id: "forensics", label: "Forensics", detail: "Pixel and PDF manipulation signals" },
  { id: "consistency", label: "Consistency", detail: "Cross-document field agreement" },
  { id: "risk", label: "Risk fusion", detail: "Bounded evidence aggregation" },
  { id: "report", label: "Report", detail: "Verification report assembled" },
] as const;

export function ProcessingScreen({ fileCount }: { fileCount?: number }) {
  const elapsed = useElapsedSeconds(true);

  return (
    <div className="mx-auto w-full max-w-2xl py-8 sm:py-14">
      <div className="eg-reveal text-center">
        <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center">
          <span className="absolute inset-0 rounded-full border-2 border-slate-200" />
          <span
            className="absolute inset-0 animate-spin rounded-full border-2 border-guard-600 border-t-transparent"
            style={{ animationDuration: "1.1s" }}
          />
          <svg
            className="relative h-7 w-7 text-guard-700"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
        </div>

        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          Analysing evidence
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-600">
          {typeof fileCount === "number" && fileCount > 0
            ? `Running the full pipeline over ${fileCount} document${fileCount === 1 ? "" : "s"}.`
            : "Running the full verification pipeline."}{" "}
          Larger bundles can take a minute or more.
        </p>
      </div>

      {/* Indeterminate bar: signals activity, promises no percentage. */}
      <div
        className="eg-reveal mt-8 h-1.5 w-full overflow-hidden rounded-full bg-slate-200"
        style={stagger(1)}
        role="progressbar"
        aria-label="Verification in progress"
        aria-busy="true"
        /* No aria-valuenow — the true progress is genuinely unknown. */
      >
        <div className="eg-indeterminate h-full w-full rounded-full bg-guard-600" />
      </div>

      <p
        className="eg-reveal tabular mt-3 text-center text-xs text-slate-500"
        style={stagger(2)}
        aria-live="polite"
      >
        {elapsed}s elapsed
      </p>

      {/* Pipeline map — what the request runs, not a progress claim. */}
      <ol className="mt-10 space-y-1">
        {PIPELINE.map((stage, i) => (
          <li
            key={stage.id}
            className="eg-slide-in flex items-start gap-3 rounded-lg px-3 py-2.5"
            style={stagger(i + 3)}
          >
            <span className="mt-1.5 flex h-2 w-2 flex-shrink-0 items-center justify-center">
              <span className="eg-breathe h-2 w-2 rounded-full bg-guard-500" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium text-slate-800">{stage.label}</span>
              <span className="block text-xs text-slate-500">{stage.detail}</span>
            </span>
          </li>
        ))}
      </ol>

      <p
        className="eg-reveal mx-auto mt-8 max-w-md text-center text-xs leading-relaxed text-slate-500"
        style={stagger(10)}
      >
        Stages are shown for context. This view reports elapsed time only — it does not
        estimate completion, because the analysis does not report intermediate progress.
      </p>
    </div>
  );
}
