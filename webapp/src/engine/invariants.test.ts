/*
  Invariants that must hold for ANY board, not just the 31 real ones.

  Every number quoted in this workstream -- render costs, sampler error, the
  dice-off gap -- was measured on the same 31 WTC2024 boards the features were
  built against. Those boards are a sample of one team's season. They are the
  best data available, but they are not a proof of generality: nothing in them
  forces the engine to behave on a board shape they happen not to contain.

  This file attacks the gap from the other side. Instead of holding boards back,
  it generates thousands of boards from a seeded PRNG -- flat, extreme, skewed,
  degenerate, across every scale -- and asserts properties that must be true of
  all of them by mathematics rather than by observation.

  A property test is worth more than a held-out board here. Holding back six
  boards would only ever tell us about six more boards; a property that survives
  4000 generated boards constrains the whole input space.

  Deterministic by construction: the PRNG is seeded, so a failure is always
  reproducible from the printed seed rather than being a flake to re-run.

  No new dependency. fast-check would give shrinking, which is a real
  convenience, but not enough to justify adding a library to a shipped app six
  days from an event.
*/

import { describe, expect, it } from "vitest";
import type { Matrix } from "./boardAnalysis";
import { dodgeMapChance, winChanceFloor } from "./avoidance";
import { protocolFloor } from "./protocol";
import { SCALES, scaleById } from "../model/scale";

/** mulberry32: small, fast, and seeded so failures reproduce exactly. */
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const N = 5; // WTC is 5v5. Nothing here should be read as supporting other sizes.

/**
 * Board shapes worth generating separately.
 *
 * Uniform random alone under-samples the dangerous cases: a real board is often
 * lopsided, and the degenerate ones (all equal, all best, all worst) are exactly
 * where an off-by-one or a divide-by-zero hides.
 */
type Shape = "uniform" | "flat" | "allBest" | "allWorst" | "skewHigh" | "skewLow" | "bimodal";

const SHAPES: Shape[] = ["uniform", "flat", "allBest", "allWorst", "skewHigh", "skewLow", "bimodal"];

function makeMatrix(shape: Shape, min: number, max: number, r: () => number): Matrix {
  const mid = (min + max) / 2;
  const pick = (): number => {
    switch (shape) {
      case "flat":
        return mid;
      case "allBest":
        return max;
      case "allWorst":
        return min;
      case "skewHigh":
        return min + (max - min) * (0.6 + 0.4 * r());
      case "skewLow":
        return min + (max - min) * 0.4 * r();
      case "bimodal":
        return r() < 0.5 ? min : max;
      default:
        return min + (max - min) * r();
    }
  };
  return Array.from({ length: N }, () => Array.from({ length: N }, pick));
}

function finite(x: number): boolean {
  return typeof x === "number" && Number.isFinite(x);
}

describe("engine invariants over generated boards", () => {
  /*
    The broad sweep. Cheap per board, so it runs over every shape and every
    scale many times: this is the one that would catch a NaN leaking out of an
    unusual rating distribution.
  */
  it("keeps win chance a probability on every shape and scale", () => {
    let checked = 0;

    for (const scale of SCALES) {
      for (const shape of SHAPES) {
        for (let s = 0; s < 12; s++) {
          const seed = 1000 + s;
          const r = rng(seed);
          const m = makeMatrix(shape, scale.min, scale.max, r);

          for (const ourTeamFirst of [true, false]) {
            const p = winChanceFloor(m, scale.min, scale.max, ourTeamFirst);
            const label = `scale=${scale.id} shape=${shape} seed=${seed} first=${ourTeamFirst}`;

            expect(finite(p), `${label} produced ${p}`).toBe(true);
            expect(p, label).toBeGreaterThanOrEqual(0);
            expect(p, label).toBeLessThanOrEqual(1);
            checked++;
          }
        }
      }
    }

    // 6 scales * 7 shapes * 12 seeds * 2 sides
    expect(checked).toBe(SCALES.length * SHAPES.length * 12 * 2);
    // ~11s: 1008 searches at roughly 6ms each. Well past vitest's 5s default,
    // so the timeout is raised deliberately rather than the sweep being thinned.
  }, 120_000);

  /*
    The degenerate boards deserve named assertions rather than only being swept
    up in the loop above, because their expected values are knowable exactly.
  */
  it("puts the degenerate boards where they belong", () => {
    for (const scale of SCALES) {
      const r = rng(7);
      const best = makeMatrix("allBest", scale.min, scale.max, r);
      const worst = makeMatrix("allWorst", scale.min, scale.max, r);

      // Every matchup maximally in our favour: we should be near certain.
      expect(winChanceFloor(best, scale.min, scale.max, true), scale.id).toBeGreaterThan(0.99);
      // Every matchup maximally against us: near hopeless.
      expect(winChanceFloor(worst, scale.min, scale.max, true), scale.id).toBeLessThan(0.01);
    }
  });

  /*
    A flat board is a coin flip by construction: every pairing is the same, so
    no protocol choice can move the number. Worth pinning because the flat board
    is also the one the UI historically refused to treat as rated.
  */
  it("prices a completely flat board as an even round", () => {
    for (const scale of SCALES) {
      const flat = makeMatrix("flat", scale.min, scale.max, rng(1));
      const p = winChanceFloor(flat, scale.min, scale.max, true);
      expect(p, `scale=${scale.id}`).toBeGreaterThan(0.3);
      expect(p, `scale=${scale.id}`).toBeLessThan(0.7);
    }
  });

  /*
    Monotonicity. This is the strongest property in the file.

    Improving one of our matchups cannot make our guaranteed win chance worse.
    Every strategy available before the change is still available after it, and
    pays at least as much, so the value of the game to us is weakly higher. If
    this ever fails it is a real bug in the search, not a modelling opinion.
  */
  it("never lets a better matchup lower our floor", () => {
    const scale = scaleById("five");
    let compared = 0;
    let moved = 0;

    for (let s = 0; s < 25; s++) {
      const seed = 5000 + s;
      const r = rng(seed);
      const m = makeMatrix("uniform", scale.min, scale.max, r);
      const before = winChanceFloor(m, scale.min, scale.max, true);

      // Perturb a handful of cells rather than all 25: same property, and it
      // keeps this test inside a few seconds.
      for (let k = 0; k < 5; k++) {
        const i = Math.floor(r() * N);
        const j = Math.floor(r() * N);
        if (m[i][j] >= scale.max - 1e-9) continue;

        const raised = m.map((row) => [...row]);
        raised[i][j] = Math.min(scale.max, m[i][j] + (scale.max - scale.min) * 0.25);

        const after = winChanceFloor(raised, scale.min, scale.max, true);
        expect(
          after,
          `seed=${seed} cell=(${i},${j}) ${m[i][j].toFixed(3)} -> ${raised[i][j].toFixed(3)}`,
        ).toBeGreaterThanOrEqual(before - 1e-9);
        compared++;
        if (after > before + 1e-9) moved++;
      }
    }

    expect(compared).toBeGreaterThan(50);
    // Guard against passing vacuously. If raising a rating never moved the
    // floor at all, the assertion above would hold no matter how broken the
    // search was, so require that the number is genuinely responsive.
    expect(moved, "raising ratings never once improved the floor").toBeGreaterThan(10);
  }, 60_000);

  /*
    Refusing a matchup is a constraint, and a constraint cannot help. So every
    price in the dodge map must be non-negative, and the baseline it is measured
    against must be the same for every entry.
  */
  it("never prices a dodge as free money", () => {
    const scale = scaleById("five");

    for (let s = 0; s < 6; s++) {
      const seed = 9000 + s;
      const m = makeMatrix("uniform", scale.min, scale.max, rng(seed));
      const map = dodgeMapChance(m, scale.min, scale.max, true);

      expect(map.length, `seed=${seed}`).toBe(N * N);

      const bases = new Set(map.map((e) => e.base.toFixed(12)));
      expect(bases.size, `seed=${seed} baseline drifted between entries`).toBe(1);

      for (const e of map) {
        expect(finite(e.base), `seed=${seed} base=${e.base}`).toBe(true);
        if (e.price === null) {
          expect(e.avoided, `seed=${seed} null price with an avoided value`).toBeNull();
          continue;
        }
        expect(finite(e.price), `seed=${seed} price=${e.price}`).toBe(true);
        expect(
          e.price,
          `seed=${seed} cell=(${e.cell.ours},${e.cell.theirs}) priced at ${e.price}`,
        ).toBeGreaterThanOrEqual(-1e-9);
      }
    }
  });

  /*
    The points-valued solver has to survive the same inputs as the chance-valued
    one. It reports a guaranteed score rather than a probability, so the bound is
    a sane range rather than [0,1].
  */
  it("keeps the points floor finite and in range on every shape", () => {
    const scale = scaleById("five");

    for (const shape of SHAPES) {
      for (let s = 0; s < 8; s++) {
        const seed = 300 + s;
        const m = makeMatrix(shape, scale.min, scale.max, rng(seed));

        for (const ourTeamFirst of [true, false]) {
          const res = protocolFloor(m, ourTeamFirst);
          const label = `shape=${shape} seed=${seed} first=${ourTeamFirst}`;
          expect(finite(res.value), `${label} value=${res.value}`).toBe(true);
          // Five matchups, each bounded by the scale.
          expect(res.value, label).toBeGreaterThanOrEqual(scale.min * N - 1e-9);
          expect(res.value, label).toBeLessThanOrEqual(scale.max * N + 1e-9);
        }
      }
    }
  });

  /*
    Scale is presentation, not information. The same board expressed on 1-5 and
    on 1-100 describes identical matchups and must produce an identical answer,
    or the scale picker silently changes the advice.
  */
  it("gives the same answer however the ratings are expressed", () => {
    const from = scaleById("five");

    for (let s = 0; s < 10; s++) {
      const seed = 4000 + s;
      const m = makeMatrix("uniform", from.min, from.max, rng(seed));
      const reference = winChanceFloor(m, from.min, from.max, true);

      for (const to of SCALES) {
        // Map each rating to the same relative position on the other scale.
        const rescaled = m.map((row) =>
          row.map((v) => to.min + ((v - from.min) / (from.max - from.min)) * (to.max - to.min)),
        );
        const got = winChanceFloor(rescaled, to.min, to.max, true);
        expect(got, `seed=${seed} ${from.id} -> ${to.id}`).toBeCloseTo(reference, 9);
      }
    }
  });
});
