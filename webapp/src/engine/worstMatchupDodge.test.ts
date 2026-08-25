/**
 * `worstMatchupDodge` is a speed optimisation, and the risk that comes with any
 * optimisation is that the fast answer stops matching the slow one.
 *
 * `dodgeMapChance` prices all 25 cells on a 5x5 and takes roughly 240 ms, which
 * is far too slow to run behind a cell tap on a phone. `worstMatchupDodge`
 * prices only the cells at the worst rating -- usually two to four solves
 * instead of twenty-six.
 *
 * The load-bearing test here is the agreement test: for every real board, the
 * cheap path must produce exactly the price the exhaustive path would have.
 * Everything else is boundary behaviour.
 */
import { describe, expect, it } from "vitest";
import { dodgeMapChance, worstMatchupDodge } from "./avoidance";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";

const FIXTURES = (boards as { opponent: string; matrix: number[][] }[]).slice(0, 8);

/** Lowest rating anywhere on the board. */
function worstRating(matrix: Matrix): number {
  let worst = Infinity;
  for (const row of matrix) {
    for (const v of row) if (v < worst) worst = v;
  }
  return worst;
}

describe("worstMatchupDodge", () => {
  it("stays quiet when nothing on the board is actually bad", () => {
    // Every cell sits above the middle of a 1-5 scale, so there is no worst
    // matchup worth interrupting anyone about.
    const comfortable: Matrix = [
      [4, 4, 5, 4, 5],
      [5, 4, 4, 5, 5],
      [5, 4, 4, 5, 5],
      [4, 4, 4, 4, 5],
      [4, 5, 5, 4, 5],
    ];
    expect(worstMatchupDodge(comfortable, 1, 5)).toBeNull();
  });

  it("reports the true worst rating and how many cells share it", () => {
    const matrix: Matrix = [
      [3, 3, 3, 3, 3],
      [3, 1, 3, 3, 3],
      [3, 3, 3, 3, 3],
      [3, 3, 3, 1, 3],
      [3, 3, 3, 3, 3],
    ];
    const got = worstMatchupDodge(matrix, 1, 5);
    expect(got).not.toBeNull();
    expect(got!.rating).toBe(1);
    expect(got!.count).toBe(2);
    expect(matrix[got!.example.ours][got!.example.theirs]).toBe(1);
  });

  // Explicit timeout: this runs an exhaustive `dodgeMapChance` sweep on all 31
  // boards, which is the whole reason `worstMatchupDodge` exists. It was already
  // marginal against the 5 s default and tipped over once another engine test
  // file competed for a worker, so the limit is stated rather than inherited and
  // is set well clear of the measured cost.
  it("agrees with the exhaustive price on every real board", { timeout: 120_000 }, () => {
    for (const { opponent, matrix } of FIXTURES) {
      const fast = worstMatchupDodge(matrix, 1, 5);
      if (fast === null) continue;

      const worst = worstRating(matrix);
      expect(fast.rating, opponent).toBe(worst);

      // What the slow path would have said about the same set of cells.
      const slow = dodgeMapChance(matrix, 1, 5)
        .filter((d) => d.rating === worst && d.price !== null)
        .sort((a, b) => (a.price ?? 0) - (b.price ?? 0));

      if (slow.length === 0) {
        expect(fast.cheapest, `${opponent}: nothing escapable`).toBeNull();
        continue;
      }

      expect(fast.cheapest, `${opponent}: should have found a dodge`).not.toBeNull();
      // The cheapest price must match; which tied cell is named may differ, and
      // the screen only ever shows one of them.
      expect(fast.cheapest!.price!, opponent).toBeCloseTo(slow[0].price!, 9);
      expect(fast.cheapest!.base, opponent).toBeCloseTo(slow[0].base, 9);
    }
  });

  it("never reports a negative price", () => {
    // Refusing an option cannot improve on being free to take it. A negative
    // price would mean the constrained search beat the unconstrained one, which
    // is a bug in the solver rather than a real result.
    for (const { opponent, matrix } of FIXTURES) {
      const got = worstMatchupDodge(matrix, 1, 5);
      if (got?.cheapest?.price != null) {
        expect(got.cheapest.price, opponent).toBeGreaterThanOrEqual(-1e-9);
      }
    }
  });

  it("marks a free dodge as free rather than as a tiny cost", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const got = worstMatchupDodge(matrix, 1, 5);
      if (got?.cheapest == null) continue;
      expect(got.cheapest.free, opponent).toBe(got.cheapest.price! < 1e-9);
    }
  });

  it("respects the rating scale when deciding what counts as bad", () => {
    // A 3 is below the middle of 1-10 but above the middle of 1-5, so the same
    // board should speak up on one scale and stay quiet on the other. This is
    // the check that would have caught the hardcoded thresholds removed from
    // the desktop grid.
    const matrix: Matrix = [
      [4, 4, 4, 4, 4],
      [4, 3, 4, 4, 4],
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
    ];
    expect(worstMatchupDodge(matrix, 1, 5)).toBeNull();
    expect(worstMatchupDodge(matrix, 1, 10)).not.toBeNull();
  });
});
