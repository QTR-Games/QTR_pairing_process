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
import { outlook } from "./opponent";
import { solveProtocol } from "./protocol";

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
