/**
 * What is holding the matchup choice actually worth?
 *
 * The pairing protocol splits two different powers between the two teams. The
 * side that does NOT open gets three matchup picks and two table picks; the
 * side that opens gets two matchup picks and three table picks. So "we choose
 * matchups" and "we choose tables" are not two separate scenarios you can pick
 * between -- they are the two halves of one trade, and this measures the price
 * of that trade in the only currency that decides a round: the chance of
 * winning three games of five.
 *
 * IMPORTANT LIMITATION, stated up front because it bounds every number below.
 * This engine assigns table choice a value of exactly zero. It has no model of
 * terrain and, by the owner's own account, should not have one -- nobody builds
 * a list for a table and nobody places the terrain. So what is measured here is
 * "holding three matchup picks versus holding two", with the compensating table
 * picks contributing nothing. The matchup figure is a measurement. The table
 * figure is not a small number; it is an unmeasured one.
 *
 * Gated like the other `measure.*` harnesses: it reports, it does not assert.
 */

import { describe, expect, it } from "vitest";
import { winChanceFloor } from "./avoidance";
import { protocolFloor } from "./protocol";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  matrix: number[][];
}

const fixtures = boards as Fixture[];

const pct = (p: number) => `${(p * 100).toFixed(1)}%`;
const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

describe.skipIf(!process.env.QTR_MEASURE)("value of the matchup half of the protocol", () => {
  it("prices holding three matchup picks against holding two", () => {
    const receiving: number[] = []; // we do NOT open: 3 matchups, 2 tables
    const opening: number[] = []; // we DO open: 2 matchups, 3 tables
    const deltas: number[] = [];
    const pointDeltas: number[] = [];

    for (const { matrix } of fixtures) {
      // ourTeamFirst === true means we are the opening team (Team B).
      const weOpen = winChanceFloor(matrix, 1, 5, true);
      const weReceive = winChanceFloor(matrix, 1, 5, false);

      opening.push(weOpen);
      receiving.push(weReceive);
      deltas.push(weReceive - weOpen);

      pointDeltas.push(protocolFloor(matrix, false).value - protocolFloor(matrix, true).value);
    }

    const better = deltas.filter((d) => d > 1e-9).length;
    const level = deltas.filter((d) => Math.abs(d) <= 1e-9).length;
    const worse = deltas.filter((d) => d < -1e-9).length;

    console.log(`
Boards: ${fixtures.length}   currency: P(win 3 of 5), guaranteed against best play

  Holding 3 matchup picks (we receive)   mean ${pct(mean(receiving))}   median ${pct(median(receiving))}
  Holding 2 matchup picks (we open)      mean ${pct(mean(opening))}   median ${pct(median(opening))}

  Difference   mean ${pct(mean(deltas))}   median ${pct(median(deltas))}
               min  ${pct(Math.min(...deltas))}   max ${pct(Math.max(...deltas))}

  Receiving strictly better on ${better}/${fixtures.length}
  Exactly level on             ${level}/${fixtures.length}
  Opening strictly better on   ${worse}/${fixtures.length}

  Same comparison in points:   mean ${mean(pointDeltas).toFixed(2)}   max ${Math.max(...pointDeltas).toFixed(2)}
`);

    expect(deltas).toHaveLength(fixtures.length);
  });
});
