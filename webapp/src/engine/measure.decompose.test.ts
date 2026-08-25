/**
 * Separating what we control from what they do to us.
 *
 * The open question behind every decision-sensitivity number so far: the swing
 * across depth-1 nodes bundles OUR opening pick together with THEIR reply, so
 * none of it was attributable. This measures the two apart.
 *
 * The decomposition:
 *
 *   choice range   = spread of guaranteed value across OUR options.
 *                    What our decision is worth, assuming they answer perfectly.
 *                    This is the part we own.
 *
 *   response range = spread of value across THEIR replies, once we have
 *                    committed to our best option. What their decision is worth
 *                    after ours is made. This is the part we do not own.
 *
 * Both are measured in round points on the same board, so they are directly
 * comparable. Whichever dominates tells us what the app should actually be for:
 * if choice dominates, the job is ranking our options. If response dominates,
 * ranking is nearly pointless and the job is showing which option gives them
 * the most opportunities to go wrong.
 *
 * Reporting harness, not a pass/fail test. Run with:
 *   npx vitest run src/engine/measure.decompose.test.ts --reporter=verbose \
 *     --disable-console-intercept
 */

import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { moveOptions, newRound, optionProfile } from "./live";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

const mean = (xs: number[]): number => xs.reduce((a, b) => a + b, 0) / xs.length;

const median = (xs: number[]): number => {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

describe.skipIf(!process.env.QTR_MEASURE)("choice vs response", () => {
  it("attributes the swing to our decision or theirs", () => {
    const rows: {
      opponent: string;
      choice: number;
      response: number;
      worstCaseResponse: number;
    }[] = [];

    for (const f of FIXTURES) {
      const s = newRound(f.matrix.length, true);
      const opts = moveOptions(f.matrix, s);
      if (opts.length < 2) continue;

      const values = opts.map((o) => o.value);
      const best = Math.max(...values);
      const choice = best - Math.min(...values);

      // Their reply matters most when measured after we have played well, so
      // take the response range under our best option rather than an average
      // that includes openings we would never choose.
      const bestOpts = opts.filter((o) => Math.abs(o.value - best) < 1e-9);
      const profiles = bestOpts
        .map((o) => optionProfile(f.matrix, s, o))
        .filter((p): p is NonNullable<typeof p> => p !== null);
      if (profiles.length === 0) continue;

      // Best case for us among tied-best openings, and the worst -- the second
      // number is what we surrender by picking a tied option carelessly.
      const response = Math.max(...profiles.map((p) => p.upside));
      const worstCaseResponse = Math.min(...profiles.map((p) => p.upside));

      rows.push({ opponent: f.opponent, choice, response, worstCaseResponse });
    }

    const choices = rows.map((r) => r.choice);
    const responses = rows.map((r) => r.response);

    const shown = [...rows].sort((a, b) => b.response - a.response).slice(0, 8);
    const lines = shown.map(
      (r) =>
        `   ${r.opponent.slice(0, 18).padEnd(19)}` +
        `our choice ${r.choice.toFixed(1).padStart(5)}   ` +
        `their reply ${r.response.toFixed(1).padStart(5)}`,
    );

    const responseDominates = rows.filter((r) => r.response > r.choice).length;
    const choiceIsZero = rows.filter((r) => r.choice < 1e-9).length;

    console.log(
      `\nSwing attributable to each side, in round points (${rows.length} boards)\n` +
        lines.join("\n") +
        `\n\n   our choice     mean ${mean(choices).toFixed(2)}   median ${median(choices).toFixed(2)}` +
        `   max ${Math.max(...choices).toFixed(1)}` +
        `\n   their reply    mean ${mean(responses).toFixed(2)}   median ${median(responses).toFixed(2)}` +
        `   max ${Math.max(...responses).toFixed(1)}` +
        `\n\n   Their reply outweighs our choice on ${responseDominates}/${rows.length} boards.` +
        `\n   Our choice is worth literally nothing on ${choiceIsZero}/${rows.length} boards` +
        ` (every opener guarantees the same).`,
    );
  });
});
