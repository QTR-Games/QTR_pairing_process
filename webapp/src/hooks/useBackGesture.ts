import { useEffect, useRef } from "react";

/**
 * Route Android's hardware/gesture back to an in-app action while a round is
 * running.
 *
 * Implemented on the History API rather than `@capacitor/app`'s `backButton`
 * listener so it needs no new dependency and so the same behaviour falls out
 * on desktop and in a browser, where the gesture is the browser's own back.
 * Capacitor's Android shell already maps the hardware button onto WebView
 * history, so a single entry is enough to catch it.
 *
 * Exactly one sentinel entry is kept alive at a time, re-pushed after each
 * press rather than one entry per undoable step. Stacking entries would make
 * the count drift from the undo depth the moment anything reset the round, and
 * a drifted count is worse than none: back presses would silently do nothing
 * until the phantom entries drained. With one sentinel, a press either undoes
 * something or falls through to the platform's own back -- leaving the round,
 * or closing the app -- which is what a captain with nothing left to undo
 * means by it.
 */
export function useBackGesture(active: boolean, canUndo: boolean, onBack: () => void) {
  // Read through refs so changing either mid-round does not tear down the
  // listener and re-push the sentinel underneath the user. Written in an
  // effect rather than during render: the handler only ever reads them after
  // commit, so there is nothing to gain from touching them earlier.
  const canUndoRef = useRef(canUndo);
  const onBackRef = useRef(onBack);
  useEffect(() => {
    canUndoRef.current = canUndo;
    onBackRef.current = onBack;
  });

  useEffect(() => {
    if (!active || typeof window === "undefined" || !window.history) return;

    const push = () => window.history.pushState({ qtrRound: true }, "");
    push();

    const onPop = () => {
      if (!canUndoRef.current) return; // Nothing to undo: let the platform have it.
      onBackRef.current();
      push();
    };

    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
      // Consume our own entry on the way out, so leaving the round does not
      // leave a press that appears to do nothing.
      if (window.history.state?.qtrRound) window.history.back();
    };
  }, [active]);
}
