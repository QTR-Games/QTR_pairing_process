/**
 * Does pricing a dodge in round-win probability change what the app would say?
 *
 * `measure.avoidance.test.ts` established that in POINTS the answer is: almost
 * never. The price is 0.000 on essentially every cell of every board, because
 * an additive objective is indifferent to which of two bad cells you eat.
 *
 * This harness asks the same question in the currency that decides a round.
 * Three things are worth knowing and none of them are assumed:
 *
 *   1. How often is a dodge actually free under P(>= 3 wins)?
 *   2. When it is not free, how much does it cost?
 *   3. Does the ORDER change -- would a captain reading the chance-valued list
 *      argue about different cells than one reading the points list?
 *
 * (3) is the one that decides whether this was worth building. A new currency
 * that reproduces the old ordering is a more expensive way to say the same
 * thing.
 *
 * Run with:
 *   $env:QTR_MEASURE=1; npx vitest run src/engine/measure.avoidanceChance.test.ts
 */
import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { avoidingFloor, dodgeMapChance, dodgeMap, type Cell } from "./avoidance";
import { protocolFloor } from "./protocol";

const FIXTURES = boards as { opponent: string; matrix: number[][] }[];

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const key = (c: Cell) => `${c.ours}${c.theirs}`;

describe.skipIf(!process.env.QTR_MEASURE)("price of a dodge, in round-win probability", () => {
  it("measures the free/expensive split and the ordering shift", { timeout: 60_000 }, () => {
    const pad = (s: string, n: number) => s.padEnd(n).slice(0, n);
    const pct = (x: number, n = 8) => `${(x * 100).toFixed(3)}%`.padStart(n);

    console.log("=".repeat(104));
    console.log("DODGE PRICE IN P(>=3 WINS) vs POINTS  --  " + FIXTURES.length + " fixture boards");
    console.log("=".repeat(104));
    console.log(
      pad("opponent", 30) +
        pad("base", 9) +
        pad("worst", 9) +
        pad("  nonfree", 10) +
        pad("ptsNonfree", 11) +
        pad("  top1same", 11) +
        pad("top3overlap", 12),
    );
    console.log("-".repeat(104));

    const worsts: number[] = [];
    const nonFreeCounts: number[] = [];
    const ptsNonFreeCounts: number[] = [];
    let top1Same = 0;
    let boardsWithAnyPrice = 0;
    const overlaps: number[] = [];

    for (const { opponent, matrix } of FIXTURES) {
      const chance = dodgeMapChance(matrix, 1, 5);
      const pts = dodgeMap(matrix, protocolFloor(matrix).value);

      const base = chance[0]?.base ?? 0;
      const priced = chance.map((d) => d.price).filter((p): p is number => p !== null);
      const worst = priced.length ? Math.max(...priced) : 0;
      const nonFree = chance.filter((d) => d.price !== null && d.price > 1e-9).length;
      const ptsNonFree = pts.filter((d) => d.price !== null && d.price > 1e-9).length;

      // Ordering comparison: most expensive first in each currency.
      const chanceRank = [...chance]
        .filter((d) => d.price !== null)
        .sort((a, b) => (b.price as number) - (a.price as number));
      const ptsRank = [...pts]
        .filter((d) => d.price !== null)
        .sort((a, b) => (b.price as number) - (a.price as number));

      const same = chanceRank[0] && ptsRank[0] && key(chanceRank[0].cell) === key(ptsRank[0].cell);
      if (same) top1Same++;

      const a3 = new Set(chanceRank.slice(0, 3).map((d) => key(d.cell)));
      const b3 = new Set(ptsRank.slice(0, 3).map((d) => key(d.cell)));
      const overlap = [...a3].filter((x) => b3.has(x)).length;
      overlaps.push(overlap);

      worsts.push(worst);
      nonFreeCounts.push(nonFree);
      ptsNonFreeCounts.push(ptsNonFree);
      if (nonFree > 0) boardsWithAnyPrice++;

      console.log(
        pad(opponent, 30) +
          pct(base, 9) +
          pct(worst, 9) +
          `${nonFree}`.padStart(9) +
          `${ptsNonFree}`.padStart(11) +
          `${same ? "yes" : "no"}`.padStart(11) +
          `${overlap}/3`.padStart(12),
      );
    }

    console.log("-".repeat(104));
    console.log(`boards with at least one priced dodge : ${boardsWithAnyPrice}/${FIXTURES.length}`);
    console.log(`mean worst-cell price                 : ${(mean(worsts) * 100).toFixed(3)}%`);
    console.log(`max  worst-cell price                 : ${(Math.max(...worsts) * 100).toFixed(3)}%`);
    console.log(`mean priced cells per board (chance)  : ${mean(nonFreeCounts).toFixed(2)} / 25`);
    console.log(`mean priced cells per board (points)  : ${mean(ptsNonFreeCounts).toFixed(2)} / 25`);
    console.log(`same most-expensive cell as points    : ${top1Same}/${FIXTURES.length}`);
    console.log(`mean top-3 overlap with points        : ${mean(overlaps).toFixed(2)} / 3`);
    console.log("=".repeat(104));
  });

  it("times a full board so the budget is known", () => {
    const { matrix } = FIXTURES[0];
    const t0 = performance.now();
    dodgeMapChance(matrix, 1, 5);
    const chanceMs = performance.now() - t0;

    const t1 = performance.now();
    dodgeMap(matrix, avoidingFloor(matrix, 0) as number);
    const pointsMs = performance.now() - t1;

    console.log(`dodgeMapChance : ${chanceMs.toFixed(1)} ms`);
    console.log(`dodgeMap       : ${pointsMs.toFixed(1)} ms`);
    console.log(`ratio          : ${(chanceMs / pointsMs).toFixed(1)}x`);
  });
});
