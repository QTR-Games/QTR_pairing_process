/**
 * How much of a gap in `outlook().expected` is real?
 *
 * `pickTieBreak` separates two equally-floored halves by their typical outcome.
 * That is only honest if the gap it reports is bigger than the sampler's own
 * error. `outlook` averages 24 sampled opponent grids, so it has a standard
 * error, and a 0.1pt "difference" may be pure noise -- which would be worse
 * than saying nothing, because it looks like advice.
 *
 * This estimates that error by comparing the shipped 24-trial figure against a
 * high-trial reference on real boards, and reports the quantiles. The threshold
 * in `pickTieBreak` is set from the number this prints.
 *
 * Run: QTR_MEASURE=1 npx vitest run src/engine/measure.tiebreak.test.ts \
 *        --reporter=verbose --disable-console-intercept
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import type { LiveState } from "./live";
import { pickOptions, pickTieBreak } from "./live";
import { outlook } from "./opponent";

const REAL = boards as unknown as { opponent: string; matrix: number[][] }[];
const REFERENCE_TRIALS = 1500;

/** Every state reachable after one opening and one pairing, for breadth. */
function sampleStates(n: number) {
  const full = (1 << n) - 1;
  const out: { ourPool: number; theirPool: number; attacker: number; attackerSide: "our" | "their" }[] = [];
  for (let a = 0; a < n; a++) {
    out.push({
      ourPool: full & ~(1 << a),
      theirPool: full,
      attacker: a,
      attackerSide: "our",
    });
  }
  return out;
}

describe.skipIf(!process.env.QTR_MEASURE)("how big a gap in typical value is real", () => {
  it("measures the 24-trial sampling error against a high-trial reference", () => {
    const errs: number[] = [];

    for (const b of REAL) {
      const matrix = b.matrix as Matrix;
      for (const st of sampleStates(matrix.length)) {
        const shipped = outlook(matrix, st, 0).expected;
        const reference = outlook(matrix, st, 0, REFERENCE_TRIALS).expected;
        errs.push(Math.abs(shipped - reference));
      }
    }

    errs.sort((x, y) => x - y);
    const q = (p: number) => errs[Math.min(errs.length - 1, Math.floor(p * errs.length))];
    const rms = Math.sqrt(errs.reduce((a, e) => a + e * e, 0) / errs.length);

    console.log(
      `\n  24-trial error vs ${REFERENCE_TRIALS}-trial reference, over ${errs.length} states:\n` +
        `    rms   ${rms.toFixed(3)}\n` +
        `    p50   ${q(0.5).toFixed(3)}\n` +
        `    p90   ${q(0.9).toFixed(3)}\n` +
        `    p99   ${q(0.99).toFixed(3)}\n` +
        `    max   ${errs[errs.length - 1].toFixed(3)}\n` +
        `  A tie-break gap must clear roughly 2x the p90 to be worth printing.\n`,
    );

    expect(errs.length).toBeGreaterThan(0);
  }, 600_000);

  it("measures the upside figure separately -- a p90 is noisier than a mean", () => {
    const errs: number[] = [];
    for (const b of REAL) {
      const m = b.matrix as Matrix;
      for (const st of sampleStates(m.length)) {
        errs.push(
          Math.abs(outlook(m, st, 0, 96).high - outlook(m, st, 0, REFERENCE_TRIALS).high),
        );
      }
    }
    errs.sort((x, y) => x - y);
    console.log(
      `\n  96-trial error in the UPSIDE (p90) figure, ${errs.length} states:\n` +
        `    p90   ${errs[Math.floor(0.9 * errs.length)].toFixed(3)}\n` +
        `    max   ${errs[errs.length - 1].toFixed(3)}\n` +
        `  Compare against the mean's 0.096 / 0.191 -- the upside rung needs\n` +
        `  its own threshold if this is materially worse.\n`,
    );
    expect(errs.length).toBeGreaterThan(0);
  }, 900_000);

  it("finds the trial count where the gap becomes real without stalling a tap", () => {
    const matrix = REAL[0].matrix as Matrix;
    const states = sampleStates(matrix.length);

    console.log("\n  trials |  p90 err |  max err | ms per call");
    console.log("  -------+----------+----------+------------");

    for (const trials of [24, 96, 192, 384]) {
      const errs: number[] = [];
      for (const b of REAL) {
        const m = b.matrix as Matrix;
        for (const st of sampleStates(m.length)) {
          errs.push(
            Math.abs(outlook(m, st, 0, trials).expected - outlook(m, st, 0, REFERENCE_TRIALS).expected),
          );
        }
      }
      errs.sort((x, y) => x - y);
      const p90 = errs[Math.floor(0.9 * errs.length)];

      const t0 = performance.now();
      for (const st of states) outlook(matrix, st, 0, trials);
      const ms = (performance.now() - t0) / states.length;

      console.log(
        `  ${String(trials).padStart(6)} | ${p90.toFixed(3).padStart(8)} | ` +
          `${errs[errs.length - 1].toFixed(3).padStart(8)} | ${ms.toFixed(1).padStart(11)}`,
      );
    }
    console.log(
      "\n  A tap computes two of these. Budget ~100ms total so the list still\n" +
        "  feels instant, and set the print threshold above the max error.\n",
    );

    expect(states.length).toBeGreaterThan(0);
  }, 900_000);

  it("reports how often a real gap actually exists to print", () => {
    let ours = 0;
    let tied = 0;
    let fired = 0;
    const gaps: number[] = [];
    const byReason: Record<string, number> = {};

    for (const b of REAL) {
      const matrix = b.matrix as Matrix;
      const n = matrix.length;
      const full = (1 << n) - 1;

      for (let a = 0; a < n; a++) {
        const s: LiveState = {
          ourPool: full & ~(1 << a),
          theirPool: full,
          attacker: a,
          attackerSide: "our",
          banked: 0,
          committed: [],
        };
        for (let i = 0; i < n; i++) {
          for (let j = i + 1; j < n; j++) {
            // i and j index *their* roster, a indexes ours -- no overlap.
            ours++;
            const picks = pickOptions(matrix, s, [i, j]);
            if (Math.abs(picks[0].value - picks[1].value) > 1e-9) continue;
            tied++;
            const tb = pickTieBreak(matrix, s, [i, j]);
            if (tb) {
              fired++;
              byReason[tb.reason] = (byReason[tb.reason] ?? 0) + 1;
              gaps.push(Math.abs(tb.value - tb.otherValue));
            }
          }
        }
      }
    }

    gaps.sort((x, y) => x - y);
    console.log(
      `\n  Offers where the pick is ours:        ${ours}\n` +
        `  ...of those, floor ties:              ${tied} (${((100 * tied) / ours).toFixed(0)}%)\n` +
        `  ...of those, a real gap to print:     ${fired} (${tied ? ((100 * fired) / tied).toFixed(0) : 0}%)\n` +
        `  ...by instrument:                     ${JSON.stringify(byReason)}\n` +
        `  UNANSWERED:                           ${tied - fired} (${((100 * (tied - fired)) / ours).toFixed(0)}% of all our picks)\n` +
        (gaps.length
          ? `  gap when it fires: median ${gaps[Math.floor(gaps.length / 2)].toFixed(2)}, ` +
            `max ${gaps[gaps.length - 1].toFixed(2)}\n`
          : "  never fires -- the typical-value instrument is not the answer\n"),
    );

    expect(ours).toBeGreaterThan(0);
  }, 900_000);
});
