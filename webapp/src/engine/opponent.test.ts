/**
 * Guards on the number that will sit next to the guaranteed total.
 *
 * `outlook` is a sampled estimate, so it cannot be asserted to a fixed value
 * without pinning the RNG into the test and making the test a tautology. What
 * CAN be asserted are the properties that make it safe to display, and those
 * are the ones that would actually hurt if they broke.
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { chanceOutlook, outlook } from "./opponent";
import { solveProtocol } from "./protocol";
import { winChanceFloor } from "./avoidance";
import { assignmentChanceExtremes, probabilityMatrix } from "./winProbability";

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

const openingState = (n: number) => ({
  ourPool: (1 << n) - 1,
  theirPool: (1 << n) - 1,
  attacker: -1,
  attackerSide: "our" as const,
});

const floorOf = (m: Matrix): number =>
  solveProtocol(m, openingState(m.length), new Map()).value;

describe("outlook", () => {
  it("is deterministic for the same board", () => {
    // A figure that moved between renders would be unusable at a table, where
    // the first response to a surprising number is to look at it again.
    const m = FIXTURES[0].matrix;
    const s = openingState(m.length);
    const a = outlook(m, s, floorOf(m));
    const b = outlook(m, s, floorOf(m));
    expect(a).toEqual(b);
  });

  /*
    `expected` is a Monte Carlo mean, and Verdict.tsx branches on it: which of
    two opposite recommendations it prints turns on `expected > tau`. Measured
    against a 4000-trial reference, 5 of the 31 saved boards sit closer to that
    line than the sampling error and one sits exactly on it, so the estimate has
    to carry its own error bar for the comparison to be able to decline.

    These are the cheap invariants. The calibration itself -- true error inside
    2 stderr on 29 of 31 boards, never outside -- is measured in
    measure.outlookNoise, which needs the 4000-trial reference and is gated.
  */
  it("reports a finite error bar, and exactly zero only when every trial agrees", () => {
    // Written to assert positivity first, which failed on Opponent 10: all 24
    // sampled opponent boards return the same outcome there, so the spread is
    // genuinely zero and `expected` is not an estimate at all but a certainty.
    //
    // That is worth keeping rather than papering over. It also makes the
    // Verdict guard behave correctly for free -- a zero bar collapses the
    // "too close to call" band to nothing, so a board with no uncertainty never
    // declines to answer.
    let certain = 0;

    for (const f of FIXTURES) {
      const o = outlook(f.matrix, openingState(f.matrix.length), floorOf(f.matrix));
      expect(Number.isFinite(o.stderr), f.opponent).toBe(true);
      expect(o.stderr, f.opponent).toBeGreaterThanOrEqual(0);

      const flat = Math.abs(o.high - o.low) < 1e-9;
      if (o.stderr === 0) {
        certain++;
        expect(flat, `${f.opponent} reports no spread but low != high`).toBe(true);
      } else {
        expect(flat, `${f.opponent} reports spread but low == high`).toBe(false);
      }
    }

    // Most boards do vary; the certain ones are the exception, not the rule.
    expect(certain).toBeLessThan(FIXTURES.length / 2);
  });

  it("shrinks the error bar as the sample grows, at roughly the 1/sqrt(n) rate", () => {
    // Not a tuning knob being asserted -- this is the property that makes the
    // bar mean anything. If it did not fall with n it would be a constant
    // wearing a statistic's clothes.
    const m = FIXTURES[0].matrix;
    const s = openingState(m.length);
    const floor = floorOf(m);

    const small = outlook(m, s, floor, 24).stderr;
    const large = outlook(m, s, floor, 384).stderr;

    expect(large).toBeLessThan(small);

    // 16x the trials should be about 4x tighter. Wide band, because 24 samples
    // estimate their own spread loosely and the point is the trend, not the
    // constant.
    const ratio = small / large;
    expect(ratio).toBeGreaterThan(2);
    expect(ratio).toBeLessThan(8);
  });

  it("gives a single trial no spread to report rather than NaN", () => {
    // Bessel's correction divides by n-1. One trial is a degenerate request,
    // but a caller making it should get an honest zero, not a number that
    // poisons every comparison downstream.
    const m = FIXTURES[0].matrix;
    const o = outlook(m, openingState(m.length), floorOf(m), 1);
    expect(o.stderr).toBe(0);
    expect(Number.isNaN(o.expected)).toBe(false);
  });

  it("orders low <= expected <= high on every real board", () => {
    // Not a mathematical necessity -- a discrete left-skewed sample really can
    // put p10 above the mean. It is a DISPLAY requirement, and `outlook` clamps
    // to guarantee it, so this asserts the clamp is doing its job.
    for (const f of FIXTURES) {
      const s = openingState(f.matrix.length);
      const o = outlook(f.matrix, s, floorOf(f.matrix));
      expect(o.low).toBeLessThanOrEqual(o.expected);
      expect(o.expected).toBeLessThanOrEqual(o.high);
    }
  });

  it("never claims a typical outcome below the guaranteed floor", () => {
    // The floor is a genuine worst case, so an expected value beneath it would
    // mean one of the two is wrong -- and it would read as nonsense on screen.
    for (const f of FIXTURES) {
      const s = openingState(f.matrix.length);
      const floor = floorOf(f.matrix);
      const o = outlook(f.matrix, s, floor);
      expect(o.expected).toBeGreaterThanOrEqual(floor - 1e-9);
      expect(o.low).toBeGreaterThanOrEqual(floor - 1e-9);
    }
  });

  it("reproduces Finding 16's optimism gap on real data", () => {
    // The headline number this whole module exists to supply. Loose bounds, so
    // it fails on a regression rather than on sampling noise.
    const gaps = FIXTURES.map((f) => {
      const s = openingState(f.matrix.length);
      const floor = floorOf(f.matrix);
      return outlook(f.matrix, s, floor).expected - floor;
    });
    const mean = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    expect(mean).toBeGreaterThan(0.8);
    expect(mean).toBeLessThan(2.2);
  });

  it("carries the passed-in floor through untouched", () => {
    const m = FIXTURES[0].matrix;
    const o = outlook(m, openingState(m.length), 12.5);
    expect(o.floor).toBe(12.5);
  });
});

/**
 * The same read in the currency that actually decides the round.
 *
 * Same shape of guard as `outlook` above and for the same reason: a sampled
 * estimate cannot be pinned to a value without the test becoming a restatement
 * of the RNG. What matters is that the number is safe to put on a screen next
 * to the guaranteed one -- ordered, bounded, and stable between renders.
 */
describe("chanceOutlook", () => {
  it("is deterministic for the same board", () => {
    const m = FIXTURES[0].matrix;
    const s = openingState(m.length);
    expect(chanceOutlook(m, s, 0, 1, 5)).toEqual(chanceOutlook(m, s, 0, 1, 5));
  });

  it("stays a probability, and never beats the best assignment on the board", () => {
    // The ceiling is the best any remaining pairing can reach, so a typical
    // case above it would mean one of the two is wrong. On screen they sit in
    // the same row of boxes, where that would be plainly visible.
    for (const f of FIXTURES) {
      const s = openingState(f.matrix.length);
      const ceiling = assignmentChanceExtremes(probabilityMatrix(f.matrix, 1, 5))[1];
      const o = chanceOutlook(f.matrix, s, 0, 1, 5);
      for (const v of [o.expected, o.low, o.high]) {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(1);
      }
      expect(o.low).toBeLessThanOrEqual(o.expected);
      expect(o.expected).toBeLessThanOrEqual(o.high);
      expect(o.high).toBeLessThanOrEqual(ceiling + 1e-9);
    }
  });

  it("never claims a typical chance below the guaranteed one", () => {
    // The chance-valued twin of the points invariant above, and the reading the
    // Board tab prints: guaranteed is what we hold if they hunt us, typical is
    // what happens when they do not, so typical below guaranteed is nonsense.
    for (const f of FIXTURES) {
      const s = openingState(f.matrix.length);
      const guaranteed = winChanceFloor(f.matrix, 1, 5, true);
      const o = chanceOutlook(f.matrix, s, guaranteed, 1, 5);
      expect(o.expected).toBeGreaterThanOrEqual(guaranteed - 1e-9);
    }
  });

  it("scores the same sampled opponents as the points read", () => {
    // Not an implementation detail: the Board tab prints both currencies in the
    // same box, one as the value and one in the note. If they were drawn
    // separately those two numbers would describe different opponents, and the
    // note would quietly stop explaining the figure above it.
    const m = FIXTURES[0].matrix;
    const s = openingState(m.length);
    // One trial, so the two readings are of a single shared sampled board and
    // any difference in the draw would show up as an unrelated pair.
    const pts = outlook(m, s, 0, 1);
    const chance = chanceOutlook(m, s, 0, 1, 5, 1);
    expect(pts.stderr).toBe(0);
    expect(chance.stderr).toBe(0);
    // Both are the single trial's own value, and neither is degenerate.
    expect(pts.expected).toBe(pts.low);
    expect(chance.expected).toBe(chance.low);
    expect(chance.expected).toBeGreaterThan(0);
  });

  it("reads a dead-even board as a coin flip", () => {
    const even = Array.from({ length: 5 }, () => Array<number>(5).fill(3));
    const o = chanceOutlook(even, openingState(5), 0.5, 1, 5);
    expect(o.expected).toBeCloseTo(0.5, 12);
    expect(o.stderr).toBe(0);
  });

  it("is scale-independent, like everything else priced in chance", () => {
    // The same board typed on 1-5 and on 1-10 is the same board. A percentage
    // that moved with the labels would be a bug the scale picker could expose
    // at an event.
    const m = FIXTURES[3].matrix;
    const stretched = m.map((row) => row.map((v) => 1 + (v - 1) * (9 / 4)));
    const s = openingState(m.length);
    expect(chanceOutlook(m, s, 0, 1, 5).expected).toBeCloseTo(
      chanceOutlook(stretched, s, 0, 1, 10).expected,
      9,
    );
  });

  it("carries the passed-in floor through untouched", () => {
    const m = FIXTURES[0].matrix;
    expect(chanceOutlook(m, openingState(m.length), 0.42, 1, 5).floor).toBe(0.42);
  });
});
