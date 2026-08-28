import { useRef } from "react";

/**
 * Press-and-hold, as a set of handlers to spread onto an element.
 *
 * A long-press rather than a tap because the elements this guards -- an
 * opponent's name in the grid header, a verdict insight card the captain is
 * reading past -- sit under a thumb that brushes them constantly; a tap-to-act
 * would fire by accident. The keyboard has no "hold", so Enter/Space fires
 * immediately -- the accessible equivalent of the gesture. Right-click is left
 * alone (`e.button !== 0` is ignored) so a context-menu handler can own it.
 *
 * Lifted verbatim from the grid's private copy (PR #96) so the verdict cards can
 * share the exact same gesture without pulling in Grid.tsx. The grid keeps its
 * own copy to avoid churn there; if a third caller appears, collapse the two.
 */
export function useLongPress(onLongPress: () => void, ms = 450) {
  const timer = useRef<number | null>(null);
  const clear = () => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  };
  return {
    onPointerDown: (e: React.PointerEvent) => {
      // Ignore anything but the primary button; a right-click is the context
      // menu, not a hold.
      if (e.button !== 0) return;
      clear();
      timer.current = window.setTimeout(() => {
        timer.current = null;
        onLongPress();
      }, ms);
    },
    onPointerUp: clear,
    onPointerLeave: clear,
    onPointerCancel: clear,
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onLongPress();
      }
    },
  };
}
