/**
 * Is "never open" a theorem or an accident of 31 boards?
 *
 * measure.openOrReceive.test.ts found that on every one of the 31 real WTC
 * boards, being Team A (making them put a player forward first) is worth >= as
 * much as being Team B. Never once worse. That is a strong pattern but 31
 * boards is 31 boards, and the claim being made -- "if you win the roll, always
 * make them open" -- would be stated to a captain as a rule.
 *
 * So hunt for a counterexample. Random boards, adversarial shapes, and small
 * boards where exhaustive-ish search is cheap. If one exists this prints it and
 * the rule becomes a default instead of a law.
 *
 * Run with:
 *   $env:QTR_MEASURE=1; npx vitest run src/engine/measure.openTheorem.test.ts
 */
import { describe, it } from "vitest";
import { protocolFloor } from "./protocol";
import type { Matrix } from "./boardAnalysis";

// Deterministic PRNG so a counterexample can be reproduced exactly.
function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randomBoard(n: number, lo: number, hi: number, rnd: () => number): Matrix {
  return Array.from({ length: n }, () =>
    Array.from({ length: n }, () => lo + Math.floor(rnd() * (hi - lo + 1))),
  );
}

describe.skipIf(!process.env.QTR_MEASURE)("is 'never open' a theorem?", () => {
  it("hunts for a board where opening beats receiving", { timeout: 300_000 }, () => {
    const rnd = mulberry32(20260825);
    let tested = 0;
    let openBetter = 0;
    let equal = 0;
    let recvBetter = 0;
    let worstOpenAdvantage = -Infinity;
    let witness: { n: number; lo: number; hi: number; matrix: Matrix; gain: number } | null = null;
    const perShape = new Map<string, { open: number; eq: number; recv: number; maxGain: number }>();

    // n=5 is the only size this measures anything about: a real 3v3 event uses
    // a different pairing process entirely, so n=3 boards generated under the
    // 5v5 protocol are not evidence about 3v3. They are kept as the odd-size
    // half of the parity check. n=4 is not a WTC format either, and is included
    // precisely because an even number of pairings changes who is forced into
    // the last matchup -- the mechanism that could flip the result.
    const shapes: { n: number; lo: number; hi: number; trials: number }[] = [
      { n: 3, lo: 1, hi: 3, trials: 4000 },
      { n: 3, lo: 1, hi: 5, trials: 4000 },
      { n: 4, lo: 1, hi: 5, trials: 3000 },
      { n: 5, lo: 1, hi: 5, trials: 2500 },
      { n: 5, lo: 1, hi: 10, trials: 2500 },
      // Degenerate/extreme shapes: all-equal, binary, and one-hot boards are
      // where ties and edge behaviour live.
      { n: 5, lo: 1, hi: 2, trials: 2000 },
      { n: 5, lo: 4, hi: 5, trials: 2000 },
    ];

    for (const { n, lo, hi, trials } of shapes) {
      const label = `n=${n} ${lo}-${hi}`;
      const acc = { open: 0, eq: 0, recv: 0, maxGain: 0 };
      perShape.set(label, acc);
      for (let t = 0; t < trials; t++) {
        const matrix = randomBoard(n, lo, hi, rnd);
        const open = protocolFloor(matrix, true).value;
        const recv = protocolFloor(matrix, false).value;
        const gain = open - recv;
        tested++;
        if (gain > 1e-9) {
          openBetter++;
          acc.open++;
          if (gain > acc.maxGain) acc.maxGain = gain;
          if (gain > worstOpenAdvantage) {
            worstOpenAdvantage = gain;
            witness = { n, lo, hi, matrix, gain };
          }
        } else if (gain < -1e-9) {
          recvBetter++;
          acc.recv++;
        } else {
          equal++;
          acc.eq++;
        }
      }
    }

    console.log("=".repeat(80));
    console.log(`COUNTEREXAMPLE HUNT -- ${tested} random boards`);
    console.log("=".repeat(80));
    console.log("shape".padEnd(14) + "openBetter".padStart(12) + "equal".padStart(10) + "recvBetter".padStart(12) + "maxOpenGain".padStart(14));
    for (const [label, a] of perShape) {
      console.log(
        label.padEnd(14) +
          `${a.open}`.padStart(12) +
          `${a.eq}`.padStart(10) +
          `${a.recv}`.padStart(12) +
          a.maxGain.toFixed(2).padStart(14),
      );
    }
    console.log("-".repeat(80));
    console.log(`opening strictly better  : ${openBetter}`);
    console.log(`identical                : ${equal}`);
    console.log(`receiving better         : ${recvBetter}`);
    if (witness) {
      console.log("-".repeat(80));
      console.log(`COUNTEREXAMPLE FOUND: n=${witness.n} ratings ${witness.lo}-${witness.hi}`);
      console.log(`opening is worth +${witness.gain.toFixed(3)} points`);
      for (const row of witness.matrix) console.log("   " + row.join(" "));
      console.log("-".repeat(80));
      console.log("=> 'always make them open' is a DEFAULT, not a law.");
    } else {
      console.log("-".repeat(80));
      console.log("no counterexample found: receiving is never worse on any board tested.");
    }
    console.log("=".repeat(80));
  });
});
