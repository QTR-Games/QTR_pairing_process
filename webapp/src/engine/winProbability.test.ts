/**
 * The rating-to-probability model and the Poisson binomial beneath it.
 *
 * These tests guard two things the rest of the engine now depends on: that the
 * mapping is genuinely scale-independent, and that the distribution maths is
 * right. A quiet error here would move every dodge price without moving any
 * test that looks like it is about dodges.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { assignmentExtremes, type Matrix } from "./boardAnalysis";
import {
  EPS,
  SPREAD,
  assignmentChanceExtremes,
  atLeast,
  committedChanceExtremes,
  distributionKey,
  extendDistribution,
  probabilityMatrix,
  roundWinChance,
  toWinProbability,
  winDistribution,
  winProbabilityFromFraction,
  winsNeeded,
} from "./winProbability";

const FIXTURES = boards as { opponent: string; matrix: Matrix }[];

describe("toWinProbability", () => {
  it("puts the midpoint of any scale at a coin flip", () => {
    expect(toWinProbability(3, 1, 5)).toBeCloseTo(0.5, 12);
    expect(toWinProbability(5.5, 1, 10)).toBeCloseTo(0.5, 12);
    expect(toWinProbability(2, 1, 3)).toBeCloseTo(0.5, 12);
  });

  it("is scale-independent: the same relative position reads the same", () => {
    // Bottom of the scale, three different scales.
    const bottom = [
      toWinProbability(1, 1, 5),
      toWinProbability(1, 1, 10),
      toWinProbability(1, 1, 3),
    ];
    for (const p of bottom) expect(p).toBeCloseTo(0.5 - SPREAD / 2, 12);

    const top = [toWinProbability(5, 1, 5), toWinProbability(10, 1, 10), toWinProbability(3, 1, 3)];
    for (const p of top) expect(p).toBeCloseTo(0.5 + SPREAD / 2, 12);
  });

  it("matches the anchors the spread was chosen for", () => {
    // "a 1 is about 8%, a 5 is about 92%"
    expect(toWinProbability(1, 1, 5)).toBeCloseTo(0.075, 6);
    expect(toWinProbability(5, 1, 5)).toBeCloseTo(0.925, 6);
  });

  it("is monotonic in the rating", () => {
    for (let r = 1; r < 10; r++) {
      expect(toWinProbability(r + 1, 1, 10)).toBeGreaterThan(toWinProbability(r, 1, 10));
    }
  });

  it("never returns a certainty, even off the end of the scale", () => {
    expect(toWinProbability(-100, 1, 5)).toBe(EPS);
    expect(toWinProbability(100, 1, 5)).toBeCloseTo(1 - EPS, 12);
  });

  it("survives a degenerate scale without dividing by zero", () => {
    expect(Number.isFinite(toWinProbability(4, 4, 4))).toBe(true);
  });
});

describe("winProbabilityFromFraction", () => {
  it("agrees cell-for-cell with toWinProbability, on any scale", () => {
    // The two must never drift: the grid prints a cell straight from its stored
    // fraction while the card prose prints the same cell through the rating, and
    // a reader comparing the two would catch a gap of a single point.
    const scales: [number, number][] = [
      [1, 5],
      [1, 10],
      [0, 100],
    ];
    for (const [min, max] of scales) {
      for (let step = 0; step <= 10; step++) {
        const fraction = step / 10;
        const rating = min + fraction * (max - min);
        expect(winProbabilityFromFraction(fraction)).toBeCloseTo(
          toWinProbability(rating, min, max),
          12,
        );
      }
    }
  });

  it("puts the midpoint fraction at a coin flip", () => {
    expect(winProbabilityFromFraction(0.5)).toBeCloseTo(0.5, 12);
  });

  it("hits the same anchors and never a certainty", () => {
    expect(winProbabilityFromFraction(0)).toBeCloseTo(0.5 - SPREAD / 2, 12);
    expect(winProbabilityFromFraction(1)).toBeCloseTo(0.5 + SPREAD / 2, 12);
    // Off the ends of the stored range it still clamps, matching toWinProbability.
    expect(winProbabilityFromFraction(-1)).toBe(EPS);
    expect(winProbabilityFromFraction(2)).toBeCloseTo(1 - EPS, 12);
  });
});

describe("probabilityMatrix", () => {
  it("maps every cell and preserves shape", () => {
    // A full 5x5 board, because that is the only size this app pairs.
    const m = [
      [1, 3, 5, 3, 1],
      [5, 3, 1, 3, 5],
      [3, 3, 3, 3, 3],
      [1, 1, 5, 5, 3],
      [5, 5, 1, 1, 3],
    ];
    const p = probabilityMatrix(m, 1, 5);
    expect(p).toHaveLength(5);
    for (const row of p) expect(row).toHaveLength(5);
    expect(p[0][1]).toBeCloseTo(0.5, 12);
    expect(p[1][0]).toBeCloseTo(0.925, 6);
  });
});

describe("winsNeeded", () => {
  it("is a strict majority of five", () => {
    expect(winsNeeded(5)).toBe(3);
  });
});

describe("winDistribution", () => {
  it("is a probability distribution", () => {
    const d = winDistribution([0.1, 0.4, 0.7, 0.9, 0.2]);
    expect(d).toHaveLength(6);
    expect(d.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
    for (const x of d) expect(x).toBeGreaterThanOrEqual(0);
  });

  it("reduces to the binomial when every game is the same", () => {
    const p = 0.3;
    const d = winDistribution([p, p, p, p, p]);
    const choose = [1, 5, 10, 10, 5, 1];
    for (let k = 0; k <= 5; k++) {
      expect(d[k]).toBeCloseTo(choose[k] * p ** k * (1 - p) ** (5 - k), 12);
    }
  });

  it("is order-independent", () => {
    const a = winDistribution([0.2, 0.5, 0.9]);
    const b = winDistribution([0.9, 0.2, 0.5]);
    for (let i = 0; i < a.length; i++) expect(a[i]).toBeCloseTo(b[i], 12);
  });

  it("handles the empty board", () => {
    expect(winDistribution([])).toEqual([1]);
  });

  it("agrees with brute-force enumeration", () => {
    const ps = [0.13, 0.44, 0.61, 0.88, 0.27];
    const brute = new Array(6).fill(0);
    for (let mask = 0; mask < 32; mask++) {
      let prob = 1;
      let wins = 0;
      for (let i = 0; i < 5; i++) {
        if (mask & (1 << i)) {
          prob *= ps[i];
          wins++;
        } else {
          prob *= 1 - ps[i];
        }
      }
      brute[wins] += prob;
    }
    const d = winDistribution(ps);
    for (let k = 0; k <= 5; k++) expect(d[k]).toBeCloseTo(brute[k], 12);
  });
});

describe("extendDistribution", () => {
  it("folding one at a time equals folding all at once", () => {
    const ps = [0.3, 0.6, 0.1];
    let d: number[] = [1];
    for (const p of ps) d = extendDistribution(d, p);
    const once = winDistribution(ps);
    for (let i = 0; i < once.length; i++) expect(d[i]).toBeCloseTo(once[i], 12);
  });
});

describe("atLeast", () => {
  it("is a survival function", () => {
    const d = winDistribution([0.5, 0.5, 0.5]);
    expect(atLeast(d, 0)).toBeCloseTo(1, 12);
    expect(atLeast(d, 4)).toBeCloseTo(0, 12);
    expect(atLeast(d, 2)).toBeCloseTo(0.5, 12);
  });

  it("is non-increasing in the threshold", () => {
    const d = winDistribution([0.2, 0.8, 0.55, 0.4, 0.9]);
    for (let k = 0; k < 5; k++) expect(atLeast(d, k)).toBeGreaterThanOrEqual(atLeast(d, k + 1));
  });

  it("treats a negative threshold as certainty", () => {
    expect(atLeast(winDistribution([0.3, 0.3]), -2)).toBeCloseTo(1, 12);
  });
});

describe("roundWinChance", () => {
  it("is a coin flip when every game is a coin flip", () => {
    expect(roundWinChance([0.5, 0.5, 0.5, 0.5, 0.5])).toBeCloseTo(0.5, 12);
  });

  it("sees what a points total cannot", () => {
    // Same expected wins, very different chance of taking the round.
    const flat = [0.5, 0.5, 0.5, 0.5, 0.5];
    const polar = [0.98, 0.98, 0.02, 0.02, 0.5];
    const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
    expect(sum(flat)).toBeCloseTo(sum(polar), 12);
    expect(roundWinChance(flat)).toBeGreaterThan(roundWinChance(polar));
  });

  it("is monotonic in any single game", () => {
    const base = [0.4, 0.4, 0.4, 0.4, 0.4];
    const better = [0.9, 0.4, 0.4, 0.4, 0.4];
    expect(roundWinChance(better)).toBeGreaterThan(roundWinChance(base));
  });
});

describe("distributionKey", () => {
  it("separates distributions that differ and joins ones that do not", () => {
    const a = winDistribution([0.3, 0.6]);
    const b = winDistribution([0.6, 0.3]);
    const c = winDistribution([0.3, 0.7]);
    // Folding the same two games in either order is the same distribution, and
    // the searches that memoise on this key depend on it collapsing to one
    // entry rather than two.
    expect(distributionKey(a)).toBe(distributionKey(b));
    expect(distributionKey(a)).not.toBe(distributionKey(c));
  });

  it("does not let float noise open a new memo entry", () => {
    // 0.1 + 0.2 is not 0.3 in binary, and a key that noticed would double the
    // size of every memo in the chance-valued searches for no gain.
    expect(distributionKey([0.1 + 0.2])).toBe(distributionKey([0.3]));
  });
});

describe("assignmentChanceExtremes", () => {
  it("brackets every assignment on the board", () => {
    // The bounds are only worth showing if nothing can fall outside them, so
    // this checks them against the assignments themselves rather than against
    // a second implementation of the same bound.
    for (const f of FIXTURES.slice(0, 6)) {
      const probs = probabilityMatrix(f.matrix, 1, 5);
      const [lo, hi] = assignmentChanceExtremes(probs);
      const n = probs.length;
      const seen: number[] = [];
      const used = new Array<boolean>(n).fill(false);
      const walk = (i: number, picked: number[]): void => {
        if (i === n) {
          seen.push(roundWinChance(picked));
          return;
        }
        for (let j = 0; j < n; j++) {
          if (used[j]) continue;
          used[j] = true;
          walk(i + 1, [...picked, probs[i][j]]);
          used[j] = false;
        }
      };
      walk(0, []);
      expect(lo).toBeCloseTo(Math.min(...seen), 12);
      expect(hi).toBeCloseTo(Math.max(...seen), 12);
    }
  });

  it("orders the pair, and puts a dead-even board on the flip", () => {
    const even = Array.from({ length: 5 }, () => Array<number>(5).fill(3));
    const [lo, hi] = assignmentChanceExtremes(probabilityMatrix(even, 1, 5));
    expect(lo).toBeCloseTo(0.5, 12);
    expect(hi).toBeCloseTo(0.5, 12);
  });

  it("separates assignments a points total cannot tell apart at all", () => {
    // Why this is not a Hungarian solve on converted numbers.
    //
    // Every cell here is `3 + a[row] + b[col]` with both offsets summing to
    // zero, so EVERY perfect assignment totals exactly 15: in points this board
    // contains no decision whatsoever, floor and ceiling alike. It still
    // contains a decision, because three wins of five is not a sum -- the
    // all-threes assignment is a coin flip and the ones that trade a 2 for a 4
    // are not.
    const a = [0, 1, -1, 0, 0];
    const b = [0, -1, 1, 0, 0];
    const board = a.map((ai) => b.map((bj) => 3 + ai + bj));

    const [pointsFloor, pointsCeiling] = assignmentExtremes(board);
    expect(pointsFloor).toBe(15);
    expect(pointsCeiling).toBe(15);

    const [lo, hi] = assignmentChanceExtremes(probabilityMatrix(board, 1, 5));
    expect(hi).toBeGreaterThan(lo);
  });

  it("survives an empty board", () => {
    expect(assignmentChanceExtremes([])).toEqual([0, 0]);
  });
});

describe("committedChanceExtremes", () => {
  it("brackets every assignment that keeps the fixed pairing", () => {
    // The chance twin of cellOutlooks, checked the same way its sibling above
    // is: against the assignments themselves, not a second copy of the bound.
    // For each fixable cell we enumerate only the assignments that keep it and
    // confirm the returned [floor, ceiling] is exactly their min and max.
    for (const f of FIXTURES.slice(0, 4)) {
      const probs = probabilityMatrix(f.matrix, 1, 5);
      const n = probs.length;
      for (let fi = 0; fi < n; fi++) {
        for (let fj = 0; fj < n; fj++) {
          const [lo, hi] = committedChanceExtremes(probs, fi, fj);
          const seen: number[] = [];
          const used = new Array<boolean>(n).fill(false);
          used[fj] = true;
          const walk = (i: number, picked: number[]): void => {
            if (i === n) {
              seen.push(roundWinChance(picked));
              return;
            }
            if (i === fi) {
              walk(i + 1, [...picked, probs[fi][fj]]);
              return;
            }
            for (let j = 0; j < n; j++) {
              if (used[j]) continue;
              used[j] = true;
              walk(i + 1, [...picked, probs[i][j]]);
              used[j] = false;
            }
          };
          walk(0, []);
          expect(lo).toBeCloseTo(Math.min(...seen), 12);
          expect(hi).toBeCloseTo(Math.max(...seen), 12);
        }
      }
    }
  });

  it("majority still counts the whole board, not the sub-board", () => {
    // Fixing one game does not lower the bar to take the round: three of five
    // wins, even once one pairing is banked. A dead-even board with one game
    // pinned to a coin flip is therefore still a coin flip overall, not the
    // 2-of-4 majority the remaining games alone would imply.
    const even = Array.from({ length: 5 }, () => Array<number>(5).fill(3));
    const [lo, hi] = committedChanceExtremes(probabilityMatrix(even, 1, 5), 0, 0);
    expect(lo).toBeCloseTo(0.5, 12);
    expect(hi).toBeCloseTo(0.5, 12);
  });

  it("agrees with the free bound when the fixed cell is the average game", () => {
    // With every game an identical coin flip, banking one of them can neither
    // help nor hurt, so the committed bounds must land on the same 0.5 the free
    // enumeration gives -- a cross-check that the seed fold is not double- or
    // under-counting the pinned game.
    const even = Array.from({ length: 5 }, () => Array<number>(5).fill(3));
    const probs = probabilityMatrix(even, 1, 5);
    const [freeLo, freeHi] = assignmentChanceExtremes(probs);
    const [lo, hi] = committedChanceExtremes(probs, 2, 4);
    expect(lo).toBeCloseTo(freeLo, 12);
    expect(hi).toBeCloseTo(freeHi, 12);
  });

  it("survives an empty board", () => {
    expect(committedChanceExtremes([], 0, 0)).toEqual([0, 0]);
  });
});
