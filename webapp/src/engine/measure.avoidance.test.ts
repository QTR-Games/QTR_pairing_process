/**
 * Does the engine's own currency reproduce the finding that motivated it?
 *
 * The free/expensive split was measured in probability space (lost P(>=3 wins))
 * over 45 saved boards: free on 36, mean 0.610%, worst 7.969%. The engine
 * carries POINTS, not probability. Those are different objectives, and a result
 * that only exists in the currency it was discovered in is not a result.
 *
 * This harness re-derives the split in points on the 31 fixture boards. What
 * matters is not that the magnitudes match -- they cannot, the units differ --
 * but that the SHAPE does: most dodges free, a minority expensive, and the
 * expensive ones concentrated on the same boards.
 *
 * Run with:  $env:QTR_MEASURE=1; npx vitest run src/engine/measure.avoidance.test.ts
 */
import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { protocolFloor } from "./protocol";
import { type Cell, dodgeMap, pricePair } from "./avoidance";

const FIXTURES = boards as { opponent: string; matrix: number[][] }[];

const worstCells = (matrix: number[][], count: number): Cell[] => {
  const cells: { cell: Cell; rating: number }[] = [];
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      cells.push({ cell: { ours: i, theirs: j }, rating: matrix[i][j] });
    }
  }
  cells.sort((a, b) => a.rating - b.rating);
  return cells.slice(0, count).map((c) => c.cell);
};

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const median = (xs: number[]) => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

describe.skipIf(!process.env.QTR_MEASURE)("price of a dodge, in points", () => {
  it("measures the free/expensive split", () => {
    const w = (s: string, n: number) => s.padEnd(n).slice(0, n);
    const f = (x: number, n = 8) => x.toFixed(3).padStart(n);

    const singles: number[] = [];
    const pairs: number[] = [];
    let pairImpossible = 0;
    let elapsed = 0;

    console.log("\n" + "=".repeat(78));
    console.log("WHAT IT COSTS TO REFUSE YOUR WORST MATCHUP  (points, we open)");
    console.log("=".repeat(78));
    console.log(
      w("opponent", 30) +
        "base".padStart(9) +
        "dodged".padStart(9) +
        "price".padStart(9) +
        "bothPrice".padStart(11),
    );

    for (const b of FIXTURES) {
      const base = protocolFloor(b.matrix, true).value;
      const [worst, second] = worstCells(b.matrix, 2);

      const t0 = performance.now();
      const map = dodgeMap(b.matrix, base, true);
      elapsed += performance.now() - t0;

      const single = map.find(
        (e) => e.cell.ours === worst.ours && e.cell.theirs === worst.theirs,
      )!;
      const pair = pricePair(b.matrix, worst, second, base, true);

      singles.push(single.price!);
      if (pair.price === null) pairImpossible++;
      else pairs.push(pair.price);

      console.log(
        w(b.opponent, 30) +
          f(base, 9) +
          f(single.avoided!, 9) +
          f(single.price!, 9) +
          (pair.price === null ? "impossible".padStart(11) : f(pair.price, 11)),
      );
    }

    const freeSingles = singles.filter((p) => p < 1e-9).length;
    const freePairs = pairs.filter((p) => p < 1e-9).length;

    console.log("\n" + "-".repeat(78));
    console.log("  WORST CELL");
    console.log(`    free (no cost at all) : ${freeSingles} / ${singles.length}`);
    console.log(`    mean price            : ${mean(singles).toFixed(3)} pts`);
    console.log(`    median                : ${median(singles).toFixed(3)} pts`);
    console.log(`    worst board           : ${Math.max(...singles).toFixed(3)} pts`);
    console.log("  WORST TWO TOGETHER");
    console.log(`    cannot dodge both     : ${pairImpossible} / ${FIXTURES.length}`);
    console.log(`    free where possible   : ${freePairs} / ${pairs.length}`);
    console.log(`    mean price            : ${mean(pairs).toFixed(3)} pts`);
    console.log(`    worst board           : ${Math.max(...pairs).toFixed(3)} pts`);
    console.log(
      `\n  dodgeMap() cost: ${(elapsed / FIXTURES.length).toFixed(1)} ms per board ` +
        `(25 constrained solves)`,
    );
  });
});
