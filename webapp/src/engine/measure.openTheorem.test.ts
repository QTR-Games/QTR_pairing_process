/**
 * Is "never open" a theorem or an accident of 31 boards?
 *
 * measure.openOrReceive.test.ts found that on every one of the 31 real WTC
 * boards, being Team A (making them put a player forward first) is worth >= as
 * much as being Team B. Never once worse. That is a strong pattern but 31
 * boards is 31 boards, and the claim being made -- "if you win the roll, always
 * make them open" -- would be stated to a captain as a rule.
 *
 * So hunt for a counterexample.
 *
 * ## Scope: 5v5 only
 *
 * Every board here is 5x5. The only other format that exists is 3v3, and 3v3
 * uses a different pairing process entirely -- not the protocol in protocol.ts
 * -- so a 3x3 board run through this search would measure nothing real. Sizes
 * that are not tournament formats are not searched either: a counterexample at
 * n=4 would be a fact about an arithmetic nobody plays.
 *
 * What varies instead is the rating scale, including two compressed ones
 * (1-2, 4-5) where ties and edge behaviour concentrate, because a rule that
 * survives a compressed scale is a rule that survives a team who rate
 * everything a 3 or a 4.
 *
 * Run with:
 *   $env:QTR_MEASURE=1; npx vitest run src/engine/measure.openTheorem.test.ts
 */
import { describe, it } from "vitest";
import { protocolFloor } from "./protocol";
import type { Matrix } from "./boardAnalysis";

const TEAM_SIZE = 5;

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

function randomBoard(lo: number, hi: number, rnd: () => number): Matrix {
  return Array.from({ length: TEAM_SIZE }, () =>
    Array.from({ length: TEAM_SIZE }, () => lo + Math.floor(rnd() * (hi - lo + 1))),
  );
}

type ShapeAcc = {
  open: number;
  eq: number;
  recv: number;
  maxGain: number;
  witness: Matrix | null;
};

describe.skipIf(!process.env.QTR_MEASURE)("is 'never open' a theorem?", () => {
  it("hunts for a 5v5 board where opening beats receiving", { timeout: 300_000 }, () => {
    const rnd = mulberry32(20260825);
    let tested = 0;
    let openBetter = 0;
    let equal = 0;
    let recvBetter = 0;
    let best: { lo: number; hi: number; matrix: Matrix; gain: number } | null = null;
    const perShape = new Map<string, ShapeAcc>();

    const shapes: { lo: number; hi: number; trials: number }[] = [
      { lo: 1, hi: 5, trials: 5000 },
      { lo: 1, hi: 10, trials: 5000 },
      // Compressed scales: where ties and edge behaviour live.
      { lo: 1, hi: 2, trials: 3000 },
      { lo: 4, hi: 5, trials: 3000 },
    ];

    for (const { lo, hi, trials } of shapes) {
      const label = `${lo}-${hi}`;
      const acc: ShapeAcc = { open: 0, eq: 0, recv: 0, maxGain: 0, witness: null };
      perShape.set(label, acc);
      for (let t = 0; t < trials; t++) {
        const matrix = randomBoard(lo, hi, rnd);
        const open = protocolFloor(matrix, true).value;
        const recv = protocolFloor(matrix, false).value;
        const gain = open - recv;
        tested++;
        if (gain > 1e-9) {
          openBetter++;
          acc.open++;
          if (gain > acc.maxGain) {
            acc.maxGain = gain;
            acc.witness = matrix;
          }
          if (!best || gain > best.gain) best = { lo, hi, matrix, gain };
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
    console.log(`COUNTEREXAMPLE HUNT -- ${tested} random 5v5 boards`);
    console.log("=".repeat(80));
    console.log(
      "scale".padEnd(10) +
        "openBetter".padStart(12) +
        "equal".padStart(10) +
        "recvBetter".padStart(12) +
        "maxOpenGain".padStart(14),
    );
    for (const [label, a] of perShape) {
      console.log(
        label.padEnd(10) +
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

    // Print a witness per scale, not just the global best -- a counterexample
    // that only exists on a 1-2 scale is a different claim from one that shows
    // up on the scale actually being used at the event.
    for (const [label, a] of perShape) {
      if (!a.witness) continue;
      console.log("-".repeat(80));
      console.log(`WITNESS on scale ${label}: opening worth +${a.maxGain.toFixed(3)} points`);
      for (const row of a.witness) console.log("   [" + row.join(", ") + "],");
    }
    console.log("=".repeat(80));
    console.log(
      best
        ? "=> 'always make them open' is a DEFAULT, not a law, even at 5v5."
        : "=> no 5v5 counterexample: receiving is never worse on any board tested.",
    );
    console.log("=".repeat(80));
  });
});
