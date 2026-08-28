/**
 * Probability-valued avoidance.
 *
 * The riskiest part of this code is not the minimax -- that mirrors a search
 * already pinned by `avoidance.test.ts` -- it is the MEMO KEY. Because
 * P(>= 3 wins) does not accumulate, the value of a subtree depends on the path
 * taken to reach it, and the cache has to know that. A key that forgot the
 * accumulated distribution would still return plausible numbers, still pass
 * every shape test, and be quietly wrong on exactly the boards that matter.
 *
 * So the central test here runs an independent, deliberately unoptimised
 * reference solver that carries the assignment as a list and evaluates
 * `roundWinChance` only at complete leaves, with no cache at all. If the fast
 * path and the reference agree on real boards, the cache is sound.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import type { ProtocolState, Side } from "./protocol";
import {
  type Cell,
  avoidingFloor,
  avoidingWinChance,
  cellBit,
  dodgeCellChance,
  dodgeMapChance,
  forbidCells,
  pricePairChance,
  winChanceFloor,
} from "./avoidance";
import { probabilityMatrix, roundWinChance, winsNeeded } from "./winProbability";

const FIXTURES = (boards as { opponent: string; matrix: number[][] }[]).slice(0, 6);

// ---------------------------------------------------------------------------
// Reference solver: no memo, no incremental distribution, no cleverness.
// ---------------------------------------------------------------------------

const bitsOf = (mask: number): number[] => {
  const out: number[] = [];
  for (let i = 0; mask >> i; i++) if (mask & (1 << i)) out.push(i);
  return out;
};

const forbids = (mask: number, ours: number, theirs: number, n: number): boolean =>
  (mask & (1 << (ours * n + theirs))) !== 0;

/** Minimax P(win the round), computed from scratch at every complete leaf. */
function referenceChance(
  probs: Matrix,
  state: ProtocolState,
  forbidden: number,
  fixed: readonly number[],
): number | null {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const n = probs.length;

  if (attacker < 0) {
    let best: number | null = null;
    for (const p of bitsOf(ourPool)) {
      const sub = referenceChance(
        probs,
        { ourPool: ourPool & ~(1 << p), theirPool, attacker: p, attackerSide: "our" },
        forbidden,
        fixed,
      );
      if (sub !== null && (best === null || sub > best)) best = sub;
    }
    return best;
  }

  const offering = attackerSide === "our" ? theirPool : ourPool;
  const candidates = bitsOf(offering);

  if (candidates.length === 0) return roundWinChance(fixed);

  if (candidates.length === 1) {
    const other = candidates[0];
    const [ours, theirs] = attackerSide === "our" ? [attacker, other] : [other, attacker];
    if (forbids(forbidden, ours, theirs, n)) return null;
    return roundWinChance([...fixed, probs[ours][theirs]]);
  }

  const defenderIsUs = attackerSide === "their";
  const attackerIsUs = attackerSide === "our";
  let chosen: number | null = null;
  let sawUnmeetable = false;

  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const pair: [number, number] = [candidates[a], candidates[b]];
      let offerValue: number | null = null;
      let offerDead = false;

      for (const picked of pair) {
        const leftover = picked === pair[0] ? pair[1] : pair[0];
        const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];

        if (forbids(forbidden, ours, theirs, n)) {
          if (!attackerIsUs) {
            offerDead = true;
            break;
          }
          continue;
        }

        const nextOur = attackerIsUs ? ourPool : ourPool & ~(1 << picked) & ~(1 << leftover);
        const nextTheir = attackerIsUs
          ? theirPool & ~(1 << picked) & ~(1 << leftover)
          : theirPool;
        const nextFixed = [...fixed, probs[ours][theirs]];
        const done = bitsOf(nextOur).length === 0 && bitsOf(nextTheir).length === 0;

        const value = done
          ? roundWinChance(nextFixed)
          : referenceChance(
              probs,
              {
                ourPool: nextOur,
                theirPool: nextTheir,
                attacker: leftover,
                attackerSide: attackerIsUs ? "their" : "our",
              },
              forbidden,
              nextFixed,
            );

        if (value === null) {
          if (!attackerIsUs) {
            offerDead = true;
            break;
          }
          continue;
        }
        if (offerValue === null) offerValue = value;
        else if (attackerIsUs ? value > offerValue : value < offerValue) offerValue = value;
      }

      const result = offerDead ? null : offerValue;
      if (result === null) {
        if (!defenderIsUs) sawUnmeetable = true;
        continue;
      }
      if (chosen === null) chosen = result;
      else if (defenderIsUs ? result > chosen : result < chosen) chosen = result;
    }
    if (sawUnmeetable) break;
  }

  return sawUnmeetable ? null : chosen;
}

const referenceFloor = (probs: Matrix, forbidden: number): number | null => {
  const n = probs.length;
  const full = (1 << n) - 1;
  return referenceChance(
    probs,
    { ourPool: full, theirPool: full, attacker: -1, attackerSide: "our" as Side },
    forbidden,
    [],
  );
};

// ---------------------------------------------------------------------------

describe("solveAvoidingChance agrees with an uncached reference", () => {
  it("reproduces the reference on every fixture, unconstrained", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const probs = probabilityMatrix(matrix, 1, 5);
      const fast = avoidingWinChance(probs, 0);
      const slow = referenceFloor(probs, 0);
      expect(fast, opponent).not.toBeNull();
      expect(fast as number, opponent).toBeCloseTo(slow as number, 9);
    }
  });

  it("reproduces the reference with a cell forbidden", () => {
    for (const { opponent, matrix } of FIXTURES.slice(0, 3)) {
      const n = matrix.length;
      const probs = probabilityMatrix(matrix, 1, 5);
      for (let ours = 0; ours < n; ours++) {
        for (let theirs = 0; theirs < n; theirs++) {
          const mask = cellBit({ ours, theirs }, n);
          const fast = avoidingWinChance(probs, mask);
          const slow = referenceFloor(probs, mask);
          const label = `${opponent} [${ours}][${theirs}]`;
          if (slow === null) {
            expect(fast, label).toBeNull();
          } else {
            expect(fast as number, label).toBeCloseTo(slow, 9);
          }
        }
      }
    }
  });
});

describe("structural agreement with the points search", () => {
  it("agrees on WHETHER a dodge is possible, cell by cell", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const n = matrix.length;
      const probs = probabilityMatrix(matrix, 1, 5);
      for (let ours = 0; ours < n; ours++) {
        for (let theirs = 0; theirs < n; theirs++) {
          const mask = cellBit({ ours, theirs }, n);
          const label = `${opponent} [${ours}][${theirs}]`;
          const pointsPossible = avoidingFloor(matrix, mask) !== null;
          const chancePossible = avoidingWinChance(probs, mask) !== null;
          expect(chancePossible, label).toBe(pointsPossible);
        }
      }
    }
  });

  it("agrees on WHETHER a pair can be dodged together", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const n = matrix.length;
      const probs = probabilityMatrix(matrix, 1, 5);
      const a: Cell = { ours: 0, theirs: 0 };
      const b: Cell = { ours: 1, theirs: 1 };
      const mask = forbidCells([a, b], n);
      expect(avoidingWinChance(probs, mask) !== null, opponent).toBe(
        avoidingFloor(matrix, mask) !== null,
      );
    }
  });
});

describe("invariants", () => {
  it("returns a probability", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const base = winChanceFloor(matrix, 1, 5);
      expect(base, opponent).toBeGreaterThanOrEqual(0);
      expect(base, opponent).toBeLessThanOrEqual(1);
    }
  });

  it("never prices a dodge below zero", () => {
    for (const { opponent, matrix } of FIXTURES) {
      for (const d of dodgeMapChance(matrix, 1, 5)) {
        if (d.price === null) continue;
        expect(d.price, `${opponent} [${d.cell.ours}][${d.cell.theirs}]`).toBeGreaterThan(-1e-9);
      }
    }
  });

  it("sorts cheapest first", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const priced = dodgeMapChance(matrix, 1, 5)
        .map((d) => d.price)
        .filter((p): p is number => p !== null);
      for (let i = 1; i < priced.length; i++) {
        expect(priced[i], opponent).toBeGreaterThanOrEqual(priced[i - 1] - 1e-12);
      }
    }
  });

  it("prices a pair at least as high as either cell alone", () => {
    for (const { matrix } of FIXTURES.slice(0, 3)) {
      const a: Cell = { ours: 0, theirs: 1 };
      const b: Cell = { ours: 2, theirs: 3 };
      const pair = pricePairChance(matrix, a, b, 1, 5);
      if (pair.price === null) continue;
      const map = dodgeMapChance(matrix, 1, 5);
      const find = (c: Cell) =>
        map.find((d) => d.cell.ours === c.ours && d.cell.theirs === c.theirs);
      for (const single of [find(a), find(b)]) {
        if (single?.price == null) continue;
        expect(pair.price).toBeGreaterThan(single.price - 1e-9);
      }
    }
  });

  it("dodgeCellChance matches dodgeMapChance cell by cell", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const n = matrix.length;
      const map = dodgeMapChance(matrix, 1, 5);
      const byCell = new Map(map.map((d) => [`${d.cell.ours},${d.cell.theirs}`, d]));
      for (let ours = 0; ours < n; ours++) {
        for (let theirs = 0; theirs < n; theirs++) {
          const one = dodgeCellChance(matrix, { ours, theirs }, 1, 5);
          const all = byCell.get(`${ours},${theirs}`)!;
          const label = `${opponent} [${ours}][${theirs}]`;
          expect(one.rating, label).toBe(all.rating);
          expect(one.base, label).toBeCloseTo(all.base, 12);
          expect(one.free, label).toBe(all.free);
          if (all.price === null) {
            expect(one.price, label).toBeNull();
            expect(one.avoided, label).toBeNull();
          } else {
            expect(one.price as number, label).toBeCloseTo(all.price, 12);
            expect(one.avoided as number, label).toBeCloseTo(all.avoided as number, 12);
          }
        }
      }
    }
  });

  it("is scale-independent: a 1-5 board and its 1-10 image agree", () => {
    for (const { opponent, matrix } of FIXTURES.slice(0, 3)) {
      // Map rating r on 1-5 to the same relative position on 1-10.
      const scaled = matrix.map((row) => row.map((r) => 1 + ((r - 1) * 9) / 4));
      expect(winChanceFloor(scaled, 1, 10), opponent).toBeCloseTo(
        winChanceFloor(matrix, 1, 5),
        9,
      );
    }
  });
});

describe("the objective is doing real work", () => {
  /**
   * The reason this whole file exists, stated as an assertion.
   *
   * In points the guaranteed total is additive, so eating one bad cell instead
   * of another shuffles the same numbers into a different order and the sum is
   * unchanged. Measured over all 31 fixtures (`measure.avoidanceChance.test.ts`)
   * the points price of a dodge is 0.000 on 775 of 775 cells -- the app cannot
   * rank dodges at all. Under P(>= 3 wins) the same boards price a mean of 10.9
   * cells each. If this assertion ever fails, the new objective has collapsed
   * back into the old one and the code below is dead weight.
   */
  it("prices dodges that the points objective calls free", () => {
    const priced = FIXTURES.map(({ matrix }) =>
      dodgeMapChance(matrix, 1, 5).filter((d) => d.price !== null && d.price > 1e-9).length,
    );
    const boardsWithAPrice = priced.filter((n) => n > 0).length;

    expect(boardsWithAPrice).toBeGreaterThan(FIXTURES.length / 2);
    expect(Math.max(...priced)).toBeGreaterThan(10);
  });

  /**
   * Where the two currencies AGREE, which is worth pinning so nobody oversells
   * the new objective.
   *
   * Spreading a board out symmetrically about the midpoint does not change
   * P(>= 3 wins) at all: two near-certain wins plus two near-certain losses plus
   * a coin flip is still exactly a coin flip. Points say the boards are equal
   * and so does chance. The claim "probability sees polarisation that points
   * cannot" is false in this shape and should not be made.
   */
  it("agrees with points when the spread is symmetric about the midpoint", () => {
    const flat: Matrix = Array.from({ length: 5 }, () => [3, 3, 3, 3, 3]);
    const symmetric: Matrix = [
      [5, 5, 5, 5, 5],
      [5, 5, 5, 5, 5],
      [3, 3, 3, 3, 3],
      [1, 1, 1, 1, 1],
      [1, 1, 1, 1, 1],
    ];
    expect(flat.flat().reduce((a, b) => a + b, 0)).toBe(
      symmetric.flat().reduce((a, b) => a + b, 0),
    );
    expect(avoidingFloor(symmetric, 0)).toBeCloseTo(avoidingFloor(flat, 0) as number, 9);
    expect(winChanceFloor(symmetric, 1, 5)).toBeCloseTo(winChanceFloor(flat, 1, 5), 9);
  });

  /**
   * And where they diverge: an ASYMMETRIC board with the same point total is a
   * different round. Three likely wins and two likely losses beats five coin
   * flips, because the round only needs three.
   */
  it("separates two boards that points calls identical when the spread is skewed", () => {
    const flat: Matrix = Array.from({ length: 5 }, () => [3, 3, 3, 3, 3]);
    const skewed: Matrix = [
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
      [2, 2, 2, 2, 2],
      [1, 1, 1, 1, 1],
    ];
    expect(flat.flat().reduce((a, b) => a + b, 0)).toBe(skewed.flat().reduce((a, b) => a + b, 0));
    expect(avoidingFloor(skewed, 0)).toBeCloseTo(avoidingFloor(flat, 0) as number, 9);
    expect(winChanceFloor(skewed, 1, 5)).toBeGreaterThan(winChanceFloor(flat, 1, 5));
  });

  it("a board we always win reads as a certainty, and one we always lose does not", () => {
    const strong = Array.from({ length: 5 }, () => new Array(5).fill(5));
    const weak = Array.from({ length: 5 }, () => new Array(5).fill(1));
    expect(winChanceFloor(strong, 1, 5)).toBeGreaterThan(0.99);
    expect(winChanceFloor(weak, 1, 5)).toBeLessThan(0.01);
  });

  it("needs three of five", () => {
    expect(winsNeeded(5)).toBe(3);
  });
});
