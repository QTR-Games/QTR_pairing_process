/**
 * The pick guidance, and the promise that it never says "your call".
 *
 * Found by driving the deployed app at phone width: at an offer, the attacking
 * side chooses which half it faces. When we hold the attacker that choice is
 * OURS, and the screen rendered two bare buttons with no values -- so tapping
 * the first one cost a point and finished the round one under the floor the app
 * had just guaranteed. `live.invariant.test.ts` covers the arithmetic; this
 * covers whether the screen actually tells you which half to take.
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import type { LiveState } from "./live";
import { currentDecision, newRound, pickOptions, pickTieBreak } from "./live";

const MATRIX = (boards as unknown as { matrix: number[][] }[])[0].matrix as Matrix;
const N = MATRIX.length;
const FULL = (1 << N) - 1;

function ourAttackerFacing(pairIsOffered: boolean): LiveState {
  return {
    ourPool: FULL & ~1,
    theirPool: FULL,
    attacker: 0,
    attackerSide: pairIsOffered ? "our" : "their",
    banked: 0,
    committed: [],
  };
}

describe("pickOptions", () => {
  it("values both halves of an offer instead of leaving them bare", () => {
    const picks = pickOptions(MATRIX, ourAttackerFacing(true), [1, 2]);
    expect(picks).toHaveLength(2);
    for (const p of picks) expect(Number.isFinite(p.value)).toBe(true);
    expect(picks.filter((p) => p.best).length).toBeGreaterThanOrEqual(1);
  });

  it("marks the half the attacker should take -- the max when the attacker is us", () => {
    const picks = pickOptions(MATRIX, ourAttackerFacing(true), [1, 2]);
    const target = Math.max(...picks.map((p) => p.value));
    for (const p of picks) expect(p.best).toBe(Math.abs(p.value - target) < 1e-9);
  });

  it("marks the min when the attacker is theirs -- they are not helping us", () => {
    const s = ourAttackerFacing(false);
    const picks = pickOptions(MATRIX, s, [1, 2]);
    const target = Math.min(...picks.map((p) => p.value));
    for (const p of picks) expect(p.best).toBe(Math.abs(p.value - target) < 1e-9);
  });

  it("agrees with the headline the offer row prints", () => {
    // The row's value and the two halves beneath it are computed from the same
    // call, so they cannot drift apart the way two independent solves would.
    const s = ourAttackerFacing(true);
    const picks = pickOptions(MATRIX, s, [1, 2]);
    const headline = Math.max(...picks.map((p) => p.value));
    expect(picks.some((p) => p.best && p.value === headline)).toBe(true);
  });
});

describe("pickTieBreak", () => {
  it("declines when the choice is not ours to make", () => {
    expect(pickTieBreak(MATRIX, ourAttackerFacing(false), [1, 2])).toBeNull();
  });

  it("declines when the floor already separates the halves", () => {
    const s = ourAttackerFacing(true);
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const picks = pickOptions(MATRIX, s, [i, j]);
        if (Math.abs(picks[0].value - picks[1].value) > 1e-9) {
          // The floor decided it; there is nothing for a second instrument to add.
          expect(pickTieBreak(MATRIX, s, [i, j])).toBeNull();
          return;
        }
      }
    }
  });

  it("names one of the two offered halves, never a third player", () => {
    const s = ourAttackerFacing(true);
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const tb = pickTieBreak(MATRIX, s, [i, j]);
        if (!tb) continue;
        expect([i, j]).toContain(tb.player);
        expect([i, j]).toContain(tb.other);
        expect(tb.player).not.toBe(tb.other);
      }
    }
  });

  it("only ever names the half its stated reason actually favours", () => {
    // 43% of our picks tie on the floor; the ladder then tries typical value,
    // then upside, then how much of their reply space punishes us.
    let seen = 0;
    const byReason: Record<string, number> = {};
    for (let a = 0; a < N; a++) {
      const s: LiveState = { ...ourAttackerFacing(true), ourPool: FULL & ~(1 << a), attacker: a };
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const tb = pickTieBreak(MATRIX, s, [i, j]);
          if (!tb) continue;
          seen++;
          byReason[tb.reason] = (byReason[tb.reason] ?? 0) + 1;
          if (tb.reason === "pressure") {
            // Fewer punishing replies is better, so this one reads the other way.
            expect(tb.value).toBeLessThan(tb.otherValue);
          } else {
            expect(tb.value).toBeGreaterThan(tb.otherValue);
          }
        }
      }
    }
    expect(seen).toBeGreaterThan(0);
  });

  it("never prints a sampled gap smaller than the sampler's own error", () => {
    // Only the `typical` rung is sampled. `measure.tiebreak.test.ts` put the
    // worst case for two 96-trial halves at 0.382; anything under that would be
    // noise wearing the costume of advice. The upside and pressure rungs are
    // exact, so they may act on any difference at all.
    for (let a = 0; a < N; a++) {
      const s: LiveState = { ...ourAttackerFacing(true), ourPool: FULL & ~(1 << a), attacker: a };
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const tb = pickTieBreak(MATRIX, s, [i, j]);
          if (tb?.reason !== "typical") continue;
          expect(tb.value - tb.otherValue).toBeGreaterThanOrEqual(0.4);
        }
      }
    }
  });

  it("is stable -- the same offer does not change its mind between taps", () => {
    // `outlook` samples, so a re-render must not produce different advice. The
    // seed is derived from the board and the pools, not from a clock.
    const s = ourAttackerFacing(true);
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const a = pickTieBreak(MATRIX, s, [i, j]);
        const b = pickTieBreak(MATRIX, s, [i, j]);
        expect(a?.player ?? null).toBe(b?.player ?? null);
        expect(a?.reason ?? null).toBe(b?.reason ?? null);
        expect(a?.value ?? null).toBe(b?.value ?? null);
      }
    }
  });
});

describe("the opening state", () => {
  it("does not offer pick guidance before an offer exists", () => {
    const s = newRound(N, true);
    expect(currentDecision(s).kind).not.toBe("offer");
  });
});
