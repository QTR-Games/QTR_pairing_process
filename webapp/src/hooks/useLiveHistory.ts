import { useCallback, useState } from "react";
import type { LiveState } from "../engine/live";

/**
 * How many steps back the round can go. A five-player round is at most a
 * couple of dozen decisions, so this is not really a cap on the round -- it is
 * a cap on how much dead state a long session can accumulate.
 */
const LIMIT = 50;

/**
 * The live round, plus the stack of states it passed through to get here.
 *
 * Undo is a snapshot stack rather than a set of inverse operations because
 * `LiveState` is small, immutable and rebuilt wholesale by every engine call:
 * `commitPairing` and friends already return a fresh object, so keeping the
 * previous one costs a reference and restoring it is exact by construction.
 * Inverting a commit by hand -- unbanking the points, returning both players
 * to their pools, working out whose attack it was -- would be a second
 * implementation of the engine's rules that could drift from the first.
 *
 * The distinction the hook exists to enforce is `advance` vs `reset`. Anything
 * the captain does *inside* a round is a step that should be undoable;
 * starting a round, switching board, or resuming one off disk is a new
 * timeline, and carrying the old stack across would let Back walk you into
 * another board's round. Only `advance` pushes.
 *
 * History is deliberately not persisted. It is a within-session convenience
 * for the pairing table, and restoring a stack across a reload would mean
 * offering to undo decisions from a round the captain may have finished hours
 * ago.
 */
export function useLiveHistory(initial: () => LiveState | null) {
  // One state object rather than two, so a step is a single atomic
  // transition. Held apart, the round and its stack could render between the
  // two writes with a state that never actually existed.
  const [{ live, past }, setAll] = useState<{
    live: LiveState | null;
    past: LiveState[];
  }>(() => ({ live: initial(), past: [] }));

  /** A step within the round: remembered, and undoable. */
  const advance = useCallback((next: LiveState) => {
    setAll((s) => ({
      live: next,
      past: s.live ? [...s.past, s.live].slice(-LIMIT) : s.past,
    }));
  }, []);

  /** A new timeline: start, resume, switch board, or clear. Not undoable. */
  const reset = useCallback((next: LiveState | null) => {
    setAll({ live: next, past: [] });
  }, []);

  /** Step back one action. A no-op when there is nothing to step back to. */
  const undo = useCallback(() => {
    setAll((s) =>
      s.past.length === 0
        ? s
        : { live: s.past[s.past.length - 1], past: s.past.slice(0, -1) },
    );
  }, []);

  return { live, advance, reset, undo, canUndo: past.length > 0 };
}
