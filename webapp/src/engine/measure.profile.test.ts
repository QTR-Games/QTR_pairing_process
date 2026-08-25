/**
 * Does the opportunity profile actually break the ties that minimax leaves?
 *
 * Reporting harness, not a pass/fail test. Run with:
 *   npx vitest run src/engine/measure.profile.test.ts --reporter=verbose \
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

describe.skipIf(!process.env.QTR_MEASURE)("opportunity profile", () => {
  it("reports how often it separates tied openers", () => {
    let boardsWithTie = 0;
    let tieBroken = 0;
    const lines: string[] = [];

    for (const f of FIXTURES) {
      const s = newRound(f.matrix.length, true);
      const opts = moveOptions(f.matrix, s);
      const best = Math.max(...opts.map((o) => o.value));
      const tied = opts.filter((o) => Math.abs(o.value - best) < 1e-9);
      if (tied.length < 2) continue;
      boardsWithTie++;

      const profiles = tied.map((o) => ({
        name: f.ourPlayers[o.ours!],
        p: optionProfile(f.matrix, s, o)!,
      }));

      const upsides = new Set(profiles.map((x) => x.p.upside.toFixed(3)));
      const risks = new Set(
        profiles.map((x) => (x.p.punishingReplies / x.p.totalReplies).toFixed(3)),
      );
      const broke = upsides.size > 1 || risks.size > 1;
      if (broke) tieBroken++;

      if (lines.length < 6) {
        lines.push(`\n${f.opponent}  (${tied.length} openers all guarantee ${best})`);
        for (const x of profiles) {
          lines.push(
            `   ${x.name.padEnd(10)} upside +${x.p.upside.toFixed(1).padStart(4)}` +
              `   punished by ${x.p.punishingReplies}/${x.p.totalReplies} of their replies`,
          );
        }
      }
    }

    console.log(lines.join("\n"));
    console.log(
      `\nBoards where the top openers tie: ${boardsWithTie}/${FIXTURES.length}` +
        `\nOf those, the profile separates them: ${tieBroken}/${boardsWithTie}`,
    );
  });
});
