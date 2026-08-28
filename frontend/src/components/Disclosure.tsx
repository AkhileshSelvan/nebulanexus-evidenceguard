import type { ReactNode } from "react";

/**
 * Progressive-disclosure primitive.
 *
 * Built on native <details>/<summary>: keyboard operable, announced correctly
 * by screen readers, and expandable with JavaScript disabled — none of which a
 * hand-rolled button+state version gives for free. Content inside is present in
 * the DOM, so nothing is hidden from find-in-page or assistive tech, only
 * collapsed by default.
 */
export function Disclosure({
  summary,
  hint,
  count,
  defaultOpen = false,
  children,
  tone = "default",
}: {
  summary: string;
  hint?: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
  tone?: "default" | "quiet";
}) {
  return (
    <details
      open={defaultOpen}
      className={`group rounded-lg border ${
        tone === "quiet" ? "border-slate-200 bg-slate-50/60" : "border-slate-200 bg-white"
      }`}
    >
      <summary
        className="eg-press flex min-h-[44px] cursor-pointer list-none items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-guard-600"
      >
        <svg
          className="h-4 w-4 flex-shrink-0 text-slate-400 transition-transform duration-200 group-open:rotate-90"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="min-w-0 flex-1 truncate text-left">{summary}</span>
        {typeof count === "number" && (
          <span className="flex-shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {count}
          </span>
        )}
        {hint && <span className="flex-shrink-0 text-xs font-normal text-slate-500">{hint}</span>}
      </summary>
      <div className="border-t border-slate-100 px-4 py-4">{children}</div>
    </details>
  );
}
