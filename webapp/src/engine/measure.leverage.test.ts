/**
 * Does "hold Pete or hold Bokur" actually say anything?
 *
 * `playerLeverage` is the feature that answers the question this app was asked
 * for most often: which player is worth keeping in hand. It is built on
 * `Math.max` over minimax values, and that is the exact statistic that turned
 * out to be worthless for ranking openings -- on a tight board their best reply
 * caps every option equally, every number collapses to the same figure, and a
 * panel that reports it is confidently telling the user nothing.
 *
 * The unit test only asserts that at least one real board separates. One board
 * out of thirty-one would pass it. This measures the real rate, and measures it
 * at later decisions too, because the opening is the single point where we
 * already know our choice is often worth zero -- leverage may well be a
 * mid-round signal rather than an opening one.
 *
 * Run with:  QTR_MEASURE=1 npx vitest run src/engine/measure.leverage.test.ts
 */
import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { commitPairing, currentDecision, moveOptions, newRound, playerLeverage } from "./live";
import type { LiveState } from "./live";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

const mean = (xs: number[]): number =>
  xs.length === 0 ? 0 : xs.reduce((a, b) => a + b, 0) / xs.length;

const median = (xs: number[]): number => {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

const spreadOf = (matrix: Matrix, s: LiveState): number | null => {
  const lev = playerLeverage(matrix, s);
  if (lev.length < 2) return null;
  return lev[0].gainFromWaiting - lev[lev.length - 1].gainFromWaiting;
};

/** Value of a state to us, from the point of view of whoever moves next. */
function stateValue(matrix: Matrix, s: LiveState): number {
  const opts = moveOptions(matrix, s);
  if (opts.length === 0) return s.banked;
  const vals = opts.map((o) => o.value);
  const d = currentDecision(s);
  // A forced pairing has no chooser, and one option either way, so max and min
  // agree; only a real decision needs the side to be taken into account.
  const owner = d.kind === "forced" || d.kind === "done" ? "our" : d.owner;
  return owner === "our" ? Math.max(...vals) : Math.min(...vals);
}

/**
 * Walk one line of best play, recording the leverage spread at each of our
 * decisions. Both sides take their top-valued option, so this is the line the
 * app would actually talk the user through.
 *
 * `currentDecision` never returns a `pick`: the offered pair lives in component
 * state, not in `LiveState`. So an offer has to be resolved here in two steps --
 * the offering side proposes the pair, then the attacking side takes whichever
 * half suits them and the other half carries forward as the next attacker.
 */
function walkBestLine(matrix: Matrix): {
  rows: { depth: number; spread: number }[];
  committed: number;
  stoppedBy: string;
} {
  let s = newRound(matrix.length, true);
  const out: { depth: number; spread: number }[] = [];
  let guard = 0;
  let stoppedBy = "complete";

  while (s.committed.length < matrix.length && guard++ < 40) {
    const d = currentDecision(s);
    if (d.kind === "done") {
      stoppedBy = "done-early";
      break;
    }

    if (d.kind === "forced") {
      s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
      continue;
    }

    if (d.owner === "our") {
      const sp = spreadOf(matrix, s);
      if (sp !== null) out.push({ depth: s.committed.length, spread: sp });
    }

    const opts = moveOptions(matrix, s);
    if (opts.length === 0) {
      stoppedBy = "no-options";
      break;
    }

    // The mover takes what is best for them: we maximise, they minimise.
    const best =
      d.owner === "our"
        ? opts.reduce((a, b) => (b.value > a.value ? b : a))
        : opts.reduce((a, b) => (b.value < a.value ? b : a));

    if (d.kind === "open") {
      const p = d.owner === "our" ? best.ours : best.theirs;
      if (p === undefined) {
        stoppedBy = "open-no-player";
        break;
      }
      s = {
        ...s,
        ourPool: d.owner === "our" ? s.ourPool & ~(1 << p) : s.ourPool,
        theirPool: d.owner === "their" ? s.theirPool & ~(1 << p) : s.theirPool,
        attacker: p,
        attackerSide: d.owner,
      };
      continue;
    }

    // An offer. The attacking side picks which half of the pair to face.
    if (best.pair === undefined) {
      stoppedBy = "offer-no-pair";
      break;
    }
    const [a, b] = best.pair;
    const picker: "our" | "their" = d.attackerSide;

    const branch = (candidate: number, other: number): LiveState =>
      commitPairing(
        matrix,
        s,
        d.attackerSide === "our" ? s.attacker : candidate,
        d.attackerSide === "our" ? candidate : s.attacker,
        other,
        d.owner,
      );

    const sa = branch(a, b);
    const sb = branch(b, a);
    const va = stateValue(matrix, sa);
    const vb = stateValue(matrix, sb);
    s = picker === "our" ? (va >= vb ? sa : sb) : va <= vb ? sa : sb;
  }
  return { rows: out, committed: s.committed.length, stoppedBy };
}

describe.skipIf(!process.env.QTR_MEASURE)("does holding a player say anything", () => {
  it("measures leverage spread at the opening and deeper in the round", () => {
    const openings: number[] = [];
    let openingSeparating = 0;

    for (const f of FIXTURES) {
      const sp = spreadOf(f.matrix, newRound(f.matrix.length, true));
      if (sp === null) continue;
      openings.push(sp);
      if (sp > 1e-9) openingSeparating++;
    }

    // Same question, but at every one of our decisions down the best line.
    const byDepth = new Map<number, number[]>();
    const stops = new Map<string, number>();
    const commitCounts: number[] = [];
    for (const f of FIXTURES) {
      const { rows, committed, stoppedBy } = walkBestLine(f.matrix);
      stops.set(stoppedBy, (stops.get(stoppedBy) ?? 0) + 1);
      commitCounts.push(committed);
      for (const { depth, spread } of rows) {
        const cur = byDepth.get(depth) ?? [];
        cur.push(spread);
        byDepth.set(depth, cur);
      }
    }

    const lines: string[] = [];
    lines.push("");
    lines.push("  Leverage spread at the OPENING");
    lines.push(`    boards            ${openings.length}`);
    lines.push(
      `    separating        ${openingSeparating}/${openings.length}` +
        `  (${((100 * openingSeparating) / Math.max(1, openings.length)).toFixed(0)}%)`,
    );
    lines.push(`    mean              ${mean(openings).toFixed(2)}`);
    lines.push(`    median            ${median(openings).toFixed(2)}`);
    lines.push(`    max               ${Math.max(...openings).toFixed(2)}`);
    lines.push("");
    lines.push("  Leverage spread BY DEPTH, down the best line");
    lines.push("    depth   n     sep      mean   median    max");

    for (const depth of [...byDepth.keys()].sort((a, b) => a - b)) {
      const xs = byDepth.get(depth) ?? [];
      const sep = xs.filter((x) => x > 1e-9).length;
      lines.push(
        `    ${String(depth).padEnd(7)}` +
          `${String(xs.length).padEnd(6)}` +
          `${`${sep}/${xs.length}`.padEnd(9)}` +
          `${mean(xs).toFixed(2).padStart(5)}` +
          `${median(xs).toFixed(2).padStart(9)}` +
          `${Math.max(...xs).toFixed(2).padStart(7)}`,
      );
    }

    const allDeep = [...byDepth.values()].flat();
    const deepSep = allDeep.filter((x) => x > 1e-9).length;
    lines.push("");
    lines.push(
      `  Across all our decisions: ${deepSep}/${allDeep.length} separate ` +
        `(${((100 * deepSep) / Math.max(1, allDeep.length)).toFixed(0)}%), ` +
        `mean ${mean(allDeep).toFixed(2)}, max ${Math.max(...allDeep).toFixed(2)}`,
    );
    lines.push("");
    lines.push("  Walk integrity (does the line reach the end of the round?)");
    lines.push(`    pairings committed  mean ${mean(commitCounts).toFixed(2)} of 5`);
    for (const [why, n] of [...stops.entries()].sort((a, b) => b[1] - a[1])) {
      lines.push(`    stopped by ${why.padEnd(16)} ${n}/${FIXTURES.length}`);
    }
    lines.push("");

    console.log(lines.join("\n"));
  });
});
