import { useCallback, useEffect, useRef } from "react";

const IDLE_EVENTS = ["mousemove", "mousedown", "keydown", "touchstart", "scroll"];
const IDLE_MS = 5 * 60 * 1000; // 5 minutes

export function useIdleTimeout(onIdle, enabled = true) {
  const timerRef = useRef(null);

  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(onIdle, IDLE_MS);
  }, [onIdle]);

  useEffect(() => {
    if (!enabled) return;

    resetTimer();
    IDLE_EVENTS.forEach((e) => window.addEventListener(e, resetTimer, { passive: true }));
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      IDLE_EVENTS.forEach((e) => window.removeEventListener(e, resetTimer));
    };
  }, [resetTimer, enabled]);
}
