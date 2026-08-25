/**
 * The rating-to-probability model and the Poisson binomial beneath it.
 *
 * These tests guard two things the rest of the engine now depends on: that the
 * mapping is genuinely scale-independent, and that the distribution maths is
 * right. A quiet error here would move every dodge price without moving any
 * test that looks like it is about dodges.
 */
import { describe, expect, it } from "vitest";
import {
  EPS,
  SPREAD,
  atLeast,
  extendDistribution,
  probabilityMatrix,
  roundWinChance,
  toWinProbability,
  winDistribution,
  winsNeeded,
} from "./winProbability";

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
