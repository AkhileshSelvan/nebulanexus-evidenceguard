/**
 * Small motion primitives. No animation library — `requestAnimationFrame` and
 * a media query are enough for what this product needs, and keeping the bundle
 * light matters more than convenience here.
 *
 * Every hook honours `prefers-reduced-motion`: values land immediately at their
 * final state rather than being withheld.
 */

import { useEffect, useRef, useState } from "react";

/** True when the user has asked the OS to reduce motion. Reacts to changes. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false,
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

/**
 * Count a number up to `target` for the score/point reveals.
 *
 * This animates the *presentation* of a value the backend already returned —
 * it never invents or extrapolates one. With reduced motion the target is
 * returned immediately.
 */
export function useCountUp(target: number, durationMs = 800): number {
  const reduced = useReducedMotion();
  const hiddenAtMount =
    typeof document !== "undefined" && document.visibilityState === "hidden";

  const [value, setValue] = useState(reduced || hiddenAtMount ? target : 0);
  const frame = useRef<number>();
  const settle = useRef<number>();

  useEffect(() => {
    // No animation wanted, or the page is not compositing: show the real
    // value immediately.
    if (reduced || (typeof document !== "undefined" && document.visibilityState === "hidden")) {
      setValue(target);
      return;
    }

    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setValue(target * eased);
      if (t < 1) frame.current = requestAnimationFrame(tick);
      else setValue(target); // land exactly on the reported value
    };

    frame.current = requestAnimationFrame(tick);

    /* SAFETY NET — this is a risk figure, so it must never be understated.
       requestAnimationFrame is paused in background/non-compositing tabs, which
       would otherwise leave the gauge frozen at 0 while the backend reported a
       high score. This timer guarantees the true value is shown even if no
       frame ever runs. */
    settle.current = window.setTimeout(() => setValue(target), durationMs + 150);

    const onVisibility = () => {
      if (document.visibilityState === "visible") return;
      setValue(target); // leaving the tab mid-animation must not strand it low
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
      if (settle.current) window.clearTimeout(settle.current);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [target, durationMs, reduced]);

  return value;
}

/** Seconds elapsed since mount. Used to report *real* processing time. */
export function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) return;
    setSeconds(0);
    const started = Date.now();
    const id = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [active]);

  return seconds;
}

/** `style={stagger(i)}` — drives the CSS `--i` custom property. */
export function stagger(index: number): React.CSSProperties {
  return { ["--i" as string]: index } as React.CSSProperties;
}
