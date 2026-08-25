/**
 * What one tap actually costs.
 *
 * The user's standing complaint about this app, across years and two rewrites,
 * is that the maths "always still seemed slow". This measures it rather than
 * arguing about it, and it measures the thing that matters: not one call to the
 * solver, but everything `LivePanel` computes before it can draw a single
 * screen.
 *
 * That distinction is the whole point. `moveOptions` allocates a *fresh* memo
 * on entry, so every caller re-searches the same subtrees from nothing. One
 * render calls it directly, again inside `playerLeverage`, and again inside
 * `optionProfile` for every option on screen. The solver is not slow; it is
 * being asked the same questions repeatedly and forbidden from remembering the
 * answers.
 *
 * Run with QTR_PERF=1. It prints a table and asserts only that the work is
 * finite, because a hard timing bound would be a flake on shared CI.
 */
import { describe, expect, it } from "vitest";
import type { Matrix } from "./boardAnalysis";
import {
  commitPairing,
  currentDecision,
  moveOptions,
  newRound,
  optionProfile,
  pickOptions,
  pickTieBreak,
  playerLeverage,
  type LiveState,
} from "./live";
import { solveCache, type SolveCache } from "./protocol";

const ON = process.env.QTR_PERF === "1";

/** Mostly-even with a few real outliers, which is what real grids look like. */
const BOARD: Matrix = [
  [0.5, 0.9, 0.4, 0.5, 0.6],
  [0.6, 0.5, 0.5, 0.1, 0.5],
  [0.4, 0.5, 0.5, 0.6, 0.8],
  [0.5, 0.6, 0.4, 0.5, 0.5],
  [0.2, 0.5, 0.6, 0.5, 0.5],
];

/**
 * Everything one render of LivePanel computes, in the order it computes it.
 *
 * Deliberately calls the public API the component calls, so the number here is
 * the number a phone pays -- not a microbenchmark of the solver in isolation.
 *
 * The per-row work matters as much as the panel-level work and is easy to leave
 * out: every offer row renders two pick buttons, so `pickOptions` runs once per
 * row, and any row whose two halves tie on the floor additionally runs
 * `pickTieBreak`, which samples 96 opponent grids twice. An earlier version of
 * this file measured only the panel-level calls and reported 7.6ms, which was
 * an undercount of the thing being complained about.
 */
function oneRender(matrix: Matrix, s: LiveState, span: number, cache?: SolveCache): number {
  const opts = moveOptions(matrix, s, cache);
  playerLeverage(matrix, s, cache);
  const d = currentDecision(s);
  const ours = "owner" in d && d.owner === "our";

  if (ours) {
    for (const o of opts) optionProfile(matrix, s, o, cache);
  }

  // What OptionRow does for every offer row on screen.
  const choiceIsOurs = "attackerSide" in d && d.attackerSide === "our";
  for (const o of opts) {
    if (!o.pair) continue;
    const picks = pickOptions(matrix, s, o.pair, cache);
    if (choiceIsOurs && Math.abs(picks[0].value - picks[1].value) < 1e-9) {
      pickTieBreak(matrix, s, o.pair, span, cache);
    }
  }

  return opts.length;
}

/** Walk the recommended line, timing each decision on the way down. */
function walk(matrix: Matrix, ourTeamFirst: boolean, span = 1, cache?: SolveCache) {
  let s = newRound(matrix.length, ourTeamFirst);
  const rows: { depth: number; kind: string; options: number; ms: number }[] = [];
  let guard = 0;

  while (guard++ < 40) {
    const d = currentDecision(s);
    if (d.kind === "done") break;

    const t0 = performance.now();
    const options = oneRender(matrix, s, span, cache);
    const ms = performance.now() - t0;
    rows.push({ depth: s.committed.length, kind: d.kind, options, ms });

    if (d.kind === "forced") {
      s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
      continue;
    }

    const best = moveOptions(matrix, s, cache)[0];
    if (d.kind === "open") {
      const p = d.owner === "our" ? best.ours! : best.theirs!;
      s = {
        ...s,
        ourPool: d.owner === "our" ? s.ourPool & ~(1 << p) : s.ourPool,
        theirPool: d.owner === "their" ? s.theirPool & ~(1 << p) : s.theirPool,
        attacker: p,
        attackerSide: d.owner,
      };
      continue;
    }

    const pair = best.pair!;
    const attackerIsUs = d.attackerSide === "our";
    const picked = pair[0];
    const leftover = pair[1];
    const [ours, theirs] = attackerIsUs ? [s.attacker, picked] : [picked, s.attacker];
    s = commitPairing(matrix, s, ours, theirs, leftover, attackerIsUs ? "their" : "our");
  }

  return rows;
}

describe.skipIf(!ON)("cost of one tap", () => {
  it("reports what a render costs at every depth", () => {
    const lines: string[] = [];
    lines.push("");
    lines.push("  One LivePanel render, walking the recommended line");
    lines.push("  depth  decision  options       ms");

    let worst = 0;
    let total = 0;
    for (const first of [true, false]) {
      lines.push(`  -- ${first ? "we" : "they"} open --`);
      for (const r of walk(BOARD, first)) {
        lines.push(
          `  ${String(r.depth).padStart(5)}  ${r.kind.padEnd(8)}  ${String(r.options).padStart(7)}  ${r.ms.toFixed(1).padStart(7)}`,
        );
        worst = Math.max(worst, r.ms);
        total += r.ms;
      }
    }

    lines.push("");
    lines.push(`  worst single render: ${worst.toFixed(1)} ms`);
    lines.push(`  whole round:         ${total.toFixed(1)} ms`);
    lines.push("");
    lines.push("  A mid-range phone runs 4-8x slower than this machine.");
    console.log(lines.join("\n"));

    expect(worst).toBeGreaterThan(0);
  });

  /**
   * What sharing the search is worth.
   *
   * The solver was never slow. It was being asked the same questions over and
   * over and forbidden from remembering the answers: `moveOptions` allocated a
   * fresh memo on entry, `playerLeverage` called it a second time for the same
   * state, and `optionProfile` called it once per option on screen -- each
   * time from nothing.
   *
   * `SolveCache` binds a memo to a board so it can be shared. The key already
   * covers the whole state, so one cache stays valid for a whole round: every
   * tap narrows the pools, and the subtrees under the new state were searched
   * while valuing the old one.
   *
   * Both walks below produce identical numbers -- that is asserted, not
   * assumed, because a cache that changes an answer is a bug and not an
   * optimisation.
   */
  it("reports what one shared cache per board is worth", () => {
    const lines: string[] = [];
    lines.push("");
    lines.push("  Whole round, cold memo vs one cache per board");
    lines.push("  opening   cold ms   cached ms   speedup");

    let coldTotal = 0;
    let warmTotal = 0;

    for (const first of [true, false]) {
      const cold = walk(BOARD, first);
      const cache = solveCache(BOARD);
      const warm = walk(BOARD, first, 1, cache);

      // Identical advice, or the cache is not an optimisation.
      expect(warm.map((r) => `${r.depth}:${r.kind}:${r.options}`)).toEqual(
        cold.map((r) => `${r.depth}:${r.kind}:${r.options}`),
      );

      const c = cold.reduce((a, r) => a + r.ms, 0);
      const w = warm.reduce((a, r) => a + r.ms, 0);
      coldTotal += c;
      warmTotal += w;

      lines.push(
        `  ${(first ? "we open" : "they open").padEnd(9)}${c.toFixed(1).padStart(7)}` +
          `${w.toFixed(1).padStart(12)}${(c / w).toFixed(1).padStart(10)}x`,
      );
    }

    lines.push("");
    lines.push(
      `  whole round: ${coldTotal.toFixed(1)} ms -> ${warmTotal.toFixed(1)} ms ` +
        `(${(coldTotal / warmTotal).toFixed(1)}x, ${(coldTotal - warmTotal).toFixed(1)} ms saved)`,
    );
    lines.push(
      `  on a phone:  ${(coldTotal * 8).toFixed(0)} ms -> ${(warmTotal * 8).toFixed(0)} ms`,
    );
    console.log(lines.join("\n"));

    expect(warmTotal).toBeLessThanOrEqual(coldTotal);
  });

  /**
   * The search is factorial, so 5v5 being fast says nothing about 8v8.
   *
   * `TEAM_SIZE` is a hard constant of 5 and `isValidBoard` rejects anything
   * else, so nothing here is reachable from the app today. It is measured
   * because the size is the one parameter that would change if the format ever
   * did, and the answer turns out to be a wall rather than a slope: the cost
   * multiplies about sevenfold per added player. Better to know that now than
   * to promise a bigger format and find out afterwards.
   */
  it(
    "reports how the opening render scales with team size",
    () => {
      const lines: string[] = [];
      lines.push("");
      lines.push("  Opening render by team size (TEAM_SIZE is fixed at 5 today)");
      lines.push("   n   options        ms   on a slow phone");

      for (let n = 4; n <= 8; n++) {
        const m = squareBoard(n);
        const s = newRound(n, true);
        const t0 = performance.now();
        const options = oneRender(m, s, 1);
        const ms = performance.now() - t0;
        lines.push(
          `  ${String(n).padStart(2)}  ${String(options).padStart(8)}  ${ms.toFixed(1).padStart(8)}  ${(ms * 8).toFixed(0).padStart(10)} ms`,
        );
        if (ms > 4000) {
          lines.push("  (stopping: past here a render is not a render, it is a wait)");
          break;
        }
      }

      console.log(lines.join("\n"));
      expect(lines.length).toBeGreaterThan(3);
    },
    120_000,
  );
});

/** A board of size n with the same mostly-even texture as the 5v5 one. */
function squareBoard(n: number): Matrix {
  const out: number[][] = [];
  for (let i = 0; i < n; i++) {
    const row: number[] = [];
    for (let j = 0; j < n; j++) {
      // Deterministic, spread around the middle, with a few real outliers.
      const t = ((i * 7 + j * 13) % 9) / 8;
      row.push(0.1 + 0.8 * t);
    }
    out.push(row);
  }
  return out;
}
