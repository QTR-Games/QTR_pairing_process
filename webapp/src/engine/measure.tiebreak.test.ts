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
import { commitPairing, currentDecision, moveOptions, pickOptions, pickTieBreak } from "./live";
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

/**
 * What separates the ties the ladder still cannot answer?
 *
 * The four-rung ladder leaves ~16% of our own picks with no reason to prefer
 * either half. Before adding a fifth rung, measure which *exact* instruments
 * actually distinguish those cases on real boards -- adding a rung that never
 * fires (as `upside` does not) costs code and buys nothing.
 *
 * Every candidate here is computed exactly from `moveOptions`, so any
 * difference it reports is real and needs no sampling threshold.
 *
 * Run: QTR_MEASURE=1 npx vitest run src/engine/measure.tiebreak.test.ts \
 *        -t "separates the ties" --reporter=verbose --disable-console-intercept
 */
describe.skipIf(!process.env.QTR_MEASURE)("what separates the ties the ladder cannot", () => {
  it("counts which exact instrument separates each unanswered tie", () => {
    /** Exact statistics over every reply they could make to a given half. */
    function probe(matrix: Matrix, s: LiveState, mine: number, pair: [number, number]) {
      const leftover = mine === pair[0] ? pair[1] : pair[0];
      const after = commitPairing(matrix, s, s.attacker, mine, leftover, "their");
      if (currentDecision(after).kind === "done") return null;

      const replies = moveOptions(matrix, after);
      const values = replies.map((r) => r.value).sort((x, y) => x - y);
      const worst = values[0];

      // If they play their strongest reply, what is left for us afterwards?
      const best = replies[0];
      let ourNext = 0;
      const nextState: LiveState = { ...after, ...best.next };
      if (currentDecision(nextState).kind !== "done") {
        const mine2 = moveOptions(matrix, nextState);
        ourNext = mine2.length ? Math.max(...mine2.map((m) => m.value)) : nextState.banked;
      } else {
        ourNext = nextState.banked;
      }

      return {
        meanReply: values.reduce((a, v) => a + v, 0) / values.length,
        secondWorst: values.length > 1 ? values[1] : worst,
        nReplies: values.length,
        spread: values[values.length - 1] - worst,
        ourNext,
      };
    }

    const sep: Record<string, number> = {};
    let unanswered = 0;
    let anySeparated = 0;

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
            const picks = pickOptions(matrix, s, [i, j]);
            if (Math.abs(picks[0].value - picks[1].value) > 1e-9) continue;
            if (pickTieBreak(matrix, s, [i, j])) continue;

            unanswered++;
            const pa = probe(matrix, s, picks[0].player, [i, j]);
            const pb = probe(matrix, s, picks[1].player, [i, j]);
            if (!pa || !pb) continue;

            let separated = false;
            for (const k of ["meanReply", "secondWorst", "nReplies", "spread", "ourNext"] as const) {
              if (Math.abs(pa[k] - pb[k]) > 1e-9) {
                sep[k] = (sep[k] ?? 0) + 1;
                separated = true;
              }
            }
            if (separated) anySeparated++;
          }
        }
      }
    }

    console.log(
      `\n  Unanswered ties:                ${unanswered}\n` +
        `  ...separable by something:      ${anySeparated} (${unanswered ? ((100 * anySeparated) / unanswered).toFixed(0) : 0}%)\n` +
        `  ...by instrument (overlapping):\n` +
        Object.entries(sep)
          .sort((x, y) => y[1] - x[1])
          .map(([k, v]) => `      ${k.padEnd(14)} ${String(v).padStart(4)} (${((100 * v) / unanswered).toFixed(0)}%)`)
          .join("\n") +
        `\n\n  An instrument that fires on few of these is not worth a rung.\n`,
    );

    expect(unanswered).toBeGreaterThan(0);
  }, 900_000);
});

/**
 * Are the ties that nothing separates actually *identical*?
 *
 * If two of their players carry the same ratings against everyone we have
 * left, then no instrument can separate them because there is nothing to
 * separate -- they are interchangeable on this board. That is not a failure
 * of the app; it is the one honest "your call", and it is worth saying out
 * loud because it tells the user their own grid has run out of opinion and
 * anything they know off-sheet (terrain, who is on form) decides it.
 *
 * Run: QTR_MEASURE=1 npx vitest run src/engine/measure.tiebreak.test.ts \
 *        -t "interchangeable" --reporter=verbose --disable-console-intercept
 */
describe.skipIf(!process.env.QTR_MEASURE)("are the unseparable ties interchangeable", () => {
  it("checks whether the two halves carry identical ratings against our pool", () => {
    let unanswered = 0;
    let identical = 0;
    let separableIdentical = 0;
    const examples: string[] = [];

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
            const picks = pickOptions(matrix, s, [i, j]);
            if (Math.abs(picks[0].value - picks[1].value) > 1e-9) continue;
            if (pickTieBreak(matrix, s, [i, j])) continue;
            unanswered++;

            // Their columns i and j, restricted to the players we still hold
            // (plus the attacker, who is about to play one of them).
            const live = (s.ourPool | (1 << s.attacker));
            let same = true;
            for (let r = 0; r < n; r++) {
              if (!(live & (1 << r))) continue;
              if (Math.abs(matrix[r][i] - matrix[r][j]) > 1e-9) { same = false; break; }
            }
            if (same) {
              identical++;
            } else if (examples.length < 3) {
              const col = (c: number) =>
                Array.from({ length: n }, (_, r) => (live & (1 << r) ? String(matrix[r][c]) : "-")).join("");
              examples.push(`${b.opponent}: their ${i} [${col(i)}] vs ${j} [${col(j)}]`);
            }
          }
        }
      }
    }

    separableIdentical = unanswered - identical;
    console.log(
      `\n  Unanswered ties:                     ${unanswered}\n` +
        `  ...where the two are IDENTICAL:      ${identical} (${((100 * identical) / unanswered).toFixed(0)}%)\n` +
        `  ...where they genuinely differ:      ${separableIdentical} (${((100 * separableIdentical) / unanswered).toFixed(0)}%)\n` +
        (examples.length ? `\n  Examples that differ but nothing separates:\n      ${examples.join("\n      ")}\n` : "") +
        `\n  Identical halves deserve "interchangeable", not silence.\n`,
    );

    expect(unanswered).toBeGreaterThan(0);
  }, 900_000);
});

/**
 * What does it cost to advise on every offer, not just the likeliest one?
 *
 * The opponent picks which pair to offer, so the row the user actually needs
 * is not the row the app recommends. Advising only the recommended row leaves
 * the real decision unlabelled. This measures the cost of computing the whole
 * ladder for every offer in a decision, which is what fixing that requires.
 *
 * Run: QTR_MEASURE=1 npx vitest run src/engine/measure.tiebreak.test.ts \
 *        -t "advise on every offer" --reporter=verbose --disable-console-intercept
 */
describe.skipIf(!process.env.QTR_MEASURE)("what it costs to advise on every offer", () => {
  it("times a full decision with the ladder run on every row", () => {
    const perDecision: number[] = [];

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
        const t0 = performance.now();
        for (let i = 0; i < n; i++) {
          for (let j = i + 1; j < n; j++) pickTieBreak(matrix, s, [i, j]);
        }
        perDecision.push(performance.now() - t0);
      }
    }

    perDecision.sort((x, y) => x - y);
    const q = (p: number) => perDecision[Math.min(perDecision.length - 1, Math.floor(p * perDecision.length))];
    console.log(
      `\n  Offers per decision:   ${(REAL[0].matrix.length * (REAL[0].matrix.length - 1)) / 2}\n` +
        `  Full ladder, all rows: median ${q(0.5).toFixed(0)}ms, p90 ${q(0.9).toFixed(0)}ms, max ${perDecision[perDecision.length - 1].toFixed(0)}ms\n` +
        `\n  Under ~100ms it can render inline; above that it needs deferring.\n`,
    );

    expect(perDecision.length).toBeGreaterThan(0);
  }, 900_000);
});
