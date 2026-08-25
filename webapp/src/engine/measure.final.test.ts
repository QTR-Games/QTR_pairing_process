/**
 * The round-five final, on its own.
 *
 * Team Irving went 4-0 and met Australia Thorny Devils on table one with the
 * event on it. They lost 2-3. This is the only board in the fixture set whose
 * real outcome is both known and consequential, so it is worth asking what the
 * engine would have said about it rather than only reporting an average over
 * 31 boards that mostly did not matter.
 *
 * Two things are being separated here and they should not be confused:
 *
 *  - what the engine says about the GRID (a measurement, reproducible)
 *  - what actually happened (one sample, and one sample cannot validate a
 *    probability -- a 60% favourite losing is not evidence the 60% was wrong)
 *
 * So this reports both and draws no causal conclusion from the result. Its
 * purpose is to answer "did the matchup/table trade matter on the board that
 * counted", which is a question about the grid alone.
 *
 * Gated behind QTR_MEASURE like the other measure.* harnesses.
 */

import { describe, expect, it } from "vitest";
import { winChanceFloor } from "./avoidance";
import { protocolFloor } from "./protocol";
import { outlook } from "./opponent";
import { evenThreshold } from "./boardAnalysis";
import { reachReport } from "./reach";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: number[][];
}

const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

/** Australia Thorny Devils is Opponent 02 in the anonymised fixtures. */
const FINAL = "Opponent 02";

describe.skipIf(!process.env.QTR_MEASURE)("the round-five final board", () => {
  it("reports what the engine says about Thorny Devils specifically", () => {
    const b = (boards as Fixture[]).find((x) => x.opponent === FINAL);
    expect(b, `${FINAL} missing from fixtures`).toBeDefined();
    if (!b) return;

    const m = b.matrix;
    const n = m.length;
    const tau = evenThreshold(n, 1, 5);

    const weOpen = winChanceFloor(m, 1, 5, true); // 2 matchups + 3 tables
    const weReceive = winChanceFloor(m, 1, 5, false); // 3 matchups + 2 tables
    const ptsOpen = protocolFloor(m, true).value;
    const ptsReceive = protocolFloor(m, false).value;
    const o = outlook(
      m,
      { ourPool: (1 << n) - 1, theirPool: (1 << n) - 1, attacker: -1, attackerSide: "our" },
      ptsOpen,
    );
    const { floors, ceilings } = reachReport(m, undefined, true);

    const shielded = floors
      .filter((f) => f.protectedByProtocol)
      .map((f) => b.ourPlayers[f.ours] || `row ${f.ours + 1}`);
    const overstated = ceilings
      .filter((c) => c.overstated)
      .map((c) => b.theirPlayers[c.theirs] || `col ${c.theirs + 1}`);

    console.log(`
================  ${FINAL} (Australia Thorny Devils)  ================

Grid, our players down the side, rated 1-5:
${m.map((row, i) => `  ${(b.ourPlayers[i] || `P${i + 1}`).padEnd(9)} ${row.join("  ")}`).join("\n")}

Threshold to take the round: beat ${tau.toFixed(1)} points

  Guaranteed, we receive (3 matchups, 2 tables)   ${ptsReceive.toFixed(1)} pts   ${pct(weReceive)}
  Guaranteed, we open    (2 matchups, 3 tables)   ${ptsOpen.toFixed(1)} pts   ${pct(weOpen)}
  Cost of opening                                 ${(ptsReceive - ptsOpen).toFixed(2)} pts   ${pct(weReceive - weOpen)}

  Typical if they play their own board            ${o.expected.toFixed(1)} pts
  Range                                           ${o.low.toFixed(1)} .. ${o.high.toFixed(1)}

  Cannot be forced into their worst matchup:      ${shielded.length ? shielded.join(", ") : "nobody"}
  Their columns that read better than they play:  ${overstated.length ? overstated.join(", ") : "none"}

What actually happened: lost 2-3.
  One sample. It cannot confirm or refute any probability above.
`);

    expect(weReceive).toBeGreaterThanOrEqual(weOpen);
  });
});
