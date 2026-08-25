/**
 * What the reach rule would actually say, board by board.
 *
 * The population rates (16% of columns overstated, 41% of rows shielded) are
 * the right numbers for deciding whether the rule is real. They are the wrong
 * numbers for deciding whether it belongs on a phone screen, because a phone
 * shows one board at a time and the question there is "how many of my five
 * players does this fire on, on a board I am actually looking at".
 *
 * A rule that fires on 41% of rows could be two players on every board, or five
 * players on 40% of boards and none on the rest. Those are very different
 * features. This measures which.
 *
 * Gated like the other `measure.*` harnesses: it reports, it does not assert.
 */

import { describe, expect, it } from "vitest";
import { forcedCeiling, forcedFloor } from "./reach";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: number[][];
}

const fixtures = boards as Fixture[];

const histogram = (counts: number[]): string =>
  [0, 1, 2, 3, 4, 5]
    .map((n) => `${n}: ${counts.filter((c) => c === n).length}`)
    .join("  ");

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

describe.skipIf(!process.env.QTR_MEASURE)("what the reach line would say per board", () => {
  it("counts how many of our five players it fires on", () => {
    const shieldedPerBoard: number[] = [];
    const overstatedPerBoard: number[] = [];
    const examples: string[] = [];

    for (const { opponent, matrix, ourPlayers, theirPlayers } of fixtures) {
      const shielded: string[] = [];
      for (let ours = 0; ours < matrix.length; ours++) {
        const f = forcedFloor(matrix, ours);
        if (f.protectedByProtocol) shielded.push(ourPlayers[ours] || `P${ours + 1}`);
      }

      const overstated: string[] = [];
      for (let theirs = 0; theirs < matrix.length; theirs++) {
        const c = forcedCeiling(matrix, theirs);
        if (c.overstated) overstated.push(theirPlayers[theirs] || `T${theirs + 1}`);
      }

      shieldedPerBoard.push(shielded.length);
      overstatedPerBoard.push(overstated.length);

      if (examples.length < 6) {
        examples.push(
          `  ${opponent.padEnd(18)} shielded ${shielded.length} [${shielded.join(", ")}]` +
            `  overstated ${overstated.length} [${overstated.join(", ")}]`,
        );
      }
    }

    const silent = shieldedPerBoard.filter((n) => n === 0).length;

    console.log(`
Boards: ${fixtures.length}

Our players who CANNOT be forced into their own worst matchup
  per board: ${histogram(shieldedPerBoard)}
  mean ${mean(shieldedPerBoard).toFixed(2)} of 5
  boards where the line says nothing at all: ${silent}/${fixtures.length}

Their players whose column reads better than it plays
  per board: ${histogram(overstatedPerBoard)}
  mean ${mean(overstatedPerBoard).toFixed(2)} of 5

Sample boards:
${examples.join("\n")}
`);

    expect(shieldedPerBoard).toHaveLength(fixtures.length);
  });
});
