/**
 * Does our advice survive an opponent who is not our mirror?
 *
 * `protocol.ts` defends its opponent model as a bound rather than a claim:
 * "the opponent here minimises OUR total on OUR OWN numbers ... whatever they
 * are actually optimising, they cannot do worse to us than the worst they could
 * do to us."
 *
 * That defence is sound for `protocolFloor` as a NUMBER. It is not sound for
 * the ADVICE built on top of it, and the reason is algebraic:
 *
 *   a side maximising a grid O = 1 - M   is maximising  sum(1 - M)
 *                                        which is minimising sum(M)
 *
 * So "opponent minimises our total" and "opponent's grid is our grid mirrored"
 * are the SAME opponent. The worst-case model and the mirror axiom that
 * Finding 12 refuted (r = -0.049 between two real teams' grids) are one model
 * wearing two sets of clothes. Ranking our openings by that value is therefore
 * still ranking them against a mirrored opponent.
 *
 * That is fine if the ranking is insensitive to the assumption. This measures
 * whether it is.
 *
 * ## Method
 *
 * The null model that Finding 12 actually supports: their grid is drawn
 * INDEPENDENTLY of ours, from the same marginal distribution of ratings. That
 * reproduces the measured near-zero correlation without inventing structure we
 * have no evidence for.
 *
 * For each board we then play the real protocol as a general-sum game -- we
 * maximise our grid, they maximise theirs -- and record what we actually score.
 * Repeat over many independent draws of their grid.
 *
 * Three numbers per opening:
 *   floor      what `protocolFloor` promises (mirror / worst-case opponent)
 *   mean       what we score against an independently-optimising opponent
 *   p10        the bad tail of that distribution -- the "bussed" case
 *
 * The question this answers: does the opening the app recommends stay the right
 * recommendation once the opponent stops being our reflection?
 *
 * Reporting harness, not a pass/fail test. Run with:
 *   QTR_MEASURE=1 npx vitest run src/engine/measure.opponent.test.ts \
 *     --reporter=verbose --disable-console-intercept
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
// Deliberately the SHIPPED solver, not a copy. The equivalence assertion below
// is only worth having if it guards the code the app actually runs.
import { solveJoint } from "./opponent";
import { solveProtocol, type ProtocolResult } from "./protocol";

/** Two grids: ours[i][j] is points to us, theirs[i][j] is points to them. */
interface Grids {
  ours: Matrix;
  theirs: Matrix;
}

interface JointValue {
  us: number;
  them: number;
}

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

const mean = (xs: number[]): number => xs.reduce((a, b) => a + b, 0) / xs.length;

const quantile = (xs: number[], q: number): number => {
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(q * s.length))];
};

/** Deterministic RNG so a surprising result can be re-examined, not re-rolled. */
function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/* ------------------------------------------------------------------ */

/** Value we can guarantee after opening with player `p`, mirror opponent. */
function floorAfterOpening(matrix: Matrix, p: number): number {
  const n = matrix.length;
  const full = (1 << n) - 1;
  const memo = new Map<string, ProtocolResult>();
  return solveProtocol(
    matrix,
    { ourPool: full & ~(1 << p), theirPool: full, attacker: p, attackerSide: "our" },
    memo,
  ).value;
}

/** Our realised total after opening with `p`, against a given opponent grid. */
function realisedAfterOpening(g: Grids, p: number, memo: Map<string, JointValue>): number {
  const n = g.ours.length;
  const full = (1 << n) - 1;
  return solveJoint(
    g,
    { ourPool: full & ~(1 << p), theirPool: full, attacker: p, attackerSide: "our" },
    memo,
  ).us;
}

describe("the mirror axiom and the worst-case bound are the same opponent", () => {
  it("mirrored-grid play reproduces single-grid minimax exactly", () => {
    // If this holds, then `protocolFloor` IS the mirror model, and Finding 12
    // applies to it. Asserted rather than argued, on every real board.
    for (const f of FIXTURES) {
      const n = f.matrix.length;
      const mirrored: Matrix = f.matrix.map((row) => row.map((v) => 1 - v));
      const g: Grids = { ours: f.matrix, theirs: mirrored };

      for (let p = 0; p < n; p++) {
        const viaMirror = realisedAfterOpening(g, p, new Map());
        const viaMinimax = floorAfterOpening(f.matrix, p);
        expect(viaMirror).toBeCloseTo(viaMinimax, 9);
      }
    }
  });
});

describe.skipIf(!process.env.QTR_MEASURE)("opponent model", () => {
  it("checks whether our recommended opening survives a non-mirror opponent", () => {
    // Marginal-preserving null: draw their ratings from the pool of real
    // ratings, independently of ours. Reproduces r ~ 0 without inventing
    // structure we have no evidence for.
    const pool: number[] = [];
    for (const f of FIXTURES) for (const row of f.matrix) for (const v of row) pool.push(v);

    const TRIALS = Number(process.env.QTR_TRIALS ?? 200);
    const rand = rng(Number(process.env.QTR_SEED ?? 20240921));

    let agree = 0;
    const regrets: number[] = [];
    const floorErrors: number[] = [];
    const rows: string[] = [];

    for (const f of FIXTURES) {
      const n = f.matrix.length;
      const openings = Array.from({ length: n }, (_, p) => p);

      const floors = openings.map((p) => floorAfterOpening(f.matrix, p));
      const appPick = floors.indexOf(Math.max(...floors));

      const realised: number[][] = openings.map(() => []);

      for (let t = 0; t < TRIALS; t++) {
        const theirs: Matrix = Array.from({ length: n }, () =>
          Array.from({ length: n }, () => pool[Math.floor(rand() * pool.length)]),
        );
        const g: Grids = { ours: f.matrix, theirs };
        const memo = new Map<string, JointValue>();
        for (const p of openings) realised[p].push(realisedAfterOpening(g, p, memo));
      }

      const means = realised.map(mean);
      const bestByMean = means.indexOf(Math.max(...means));
      if (bestByMean === appPick) agree++;

      const regret = means[bestByMean] - means[appPick];
      regrets.push(regret);

      // How far the promised floor sits from what actually happens.
      floorErrors.push(means[appPick] - floors[appPick]);

      rows.push(
        `${f.opponent.padEnd(16)} app=${f.ourPlayers[appPick].padEnd(10)} ` +
          `floor=${floors[appPick].toFixed(2)} mean=${means[appPick].toFixed(2)} ` +
          `p10=${quantile(realised[appPick], 0.1).toFixed(2)} | ` +
          `best=${f.ourPlayers[bestByMean].padEnd(10)} regret=${regret.toFixed(2)}`,
      );
    }

    console.log("\n=== Does the recommended opening survive a non-mirror opponent? ===");
    console.log(`trials per board: ${TRIALS}, boards: ${FIXTURES.length}\n`);
    for (const r of rows) console.log(r);
    console.log(
      `\nagreement: ${agree}/${FIXTURES.length} ` +
        `(${((100 * agree) / FIXTURES.length).toFixed(0)}%)  <-- SEED-UNSTABLE, do not quote`,
    );
    console.log(`mean regret from following the floor ranking: ${mean(regrets).toFixed(3)} pts`);
    console.log(`max regret: ${Math.max(...regrets).toFixed(3)} pts`);
    console.log(
      `floor understates realised score by: mean ${mean(floorErrors).toFixed(3)} pts, ` +
        `max ${Math.max(...floorErrors).toFixed(3)}`,
    );
    console.log(
      "\nAgreement swings 29-39% across seeds 1/2/3/20240921 -- which opening wins\n" +
        "the mean comparison is not identifiable, because the openings are too close\n" +
        "to separate. Regret (0.069-0.074) and floor error (1.396-1.403) ARE stable.\n" +
        "Re-check with QTR_SEED before quoting any number from this harness.",
    );
    // ~6s at the default 200 trials, and QTR_TRIALS can raise that deliberately.
  }, 120_000);
});
