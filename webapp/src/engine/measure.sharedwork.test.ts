/**
 * Is the "shared work" in avoidance.ts actually worth sharing?
 *
 * A standing note in this workstream claimed waste: winChanceFloor (774),
 * dodgeMapChance (792), pricePairChance (834) and worstMatchupDodge (905) each
 * rebuild `probabilityMatrix` from the same board, and a desktop render was said
 * to compute the same unconstrained baseline three times. The implied fix was to
 * hoist the matrix and the baseline and pass them in.
 *
 * Before doing that surgery to a shipped engine, this measures the ceiling of
 * the saving. Two facts decide it:
 *
 *   1. probabilityMatrix is O(n^2) arithmetic. avoidingWinChance is an
 *      exponential search over pool subsets. If the first is a rounding error
 *      against the second, hoisting it saves nothing worth the risk.
 *   2. dodgeMapChance makes 26 avoidingWinChance calls -- one baseline plus one
 *      per cell. Sharing the baseline with winChanceFloor removes exactly one of
 *      those 26, so the ceiling is ~1/26 of its cost no matter how it is written.
 *
 * The desktop's two winChanceFloor calls are NOT redundant with each other:
 * Currencies.tsx:45-52 passes ourTeamFirst true and false, which are different
 * searches answering "we nominate first" and "they nominate first".
 *
 * Run: QTR_MEASURE=1 npx vitest run src/engine/measure.sharedwork.test.ts \
 *        --reporter=verbose --disable-console-intercept
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { avoidingWinChance, dodgeMapChance, winChanceFloor } from "./avoidance";
import { probabilityMatrix } from "./winProbability";

const REAL = (boards as unknown as { opponent: string; matrix: number[][] }[]).map(
  (b) => b.matrix as Matrix,
);

/** Min-of-k, to report the floor rather than a scheduler artefact. */
function best(k: number, fn: () => void): number {
  let min = Infinity;
  for (let i = 0; i < k; i++) {
    const t0 = performance.now();
    fn();
    min = Math.min(min, performance.now() - t0);
  }
  return min;
}

describe.skipIf(!process.env.QTR_MEASURE)("shared work in avoidance", () => {
  it("prices probabilityMatrix against the search it feeds", { timeout: 600_000 }, () => {
    // Warm the JIT.
    for (const m of REAL.slice(0, 3)) {
      probabilityMatrix(m, 1, 5);
      avoidingWinChance(probabilityMatrix(m, 1, 5), 0, true);
    }

    let matrixTotal = 0;
    let searchTotal = 0;

    for (const m of REAL) {
      matrixTotal += best(5, () => {
        probabilityMatrix(m, 1, 5);
      });
      const probs = probabilityMatrix(m, 1, 5);
      searchTotal += best(5, () => {
        avoidingWinChance(probs, 0, true);
      });
    }

    const n = REAL.length;
    const share = (matrixTotal / (matrixTotal + searchTotal)) * 100;

    console.log(
      `\n  Per board, mean of ${n} real boards:\n` +
        `    probabilityMatrix   ${(matrixTotal / n).toFixed(4)} ms\n` +
        `    avoidingWinChance   ${(searchTotal / n).toFixed(4)} ms\n` +
        `    matrix is ${share.toFixed(2)}% of one baseline call\n` +
        `\n  winChanceFloor = 1 matrix + 1 search. Hoisting the matrix out of a\n` +
        `  second caller therefore saves at most ${share.toFixed(2)}% of one call.\n`,
    );

    // The claim under test: the matrix is negligible against the search.
    expect(matrixTotal).toBeLessThan(searchTotal);
  });

  it("prices the shareable baseline against the whole dodge map", { timeout: 600_000 }, () => {
    for (const m of REAL.slice(0, 3)) dodgeMapChance(m, 1, 5);

    let floorTotal = 0;
    let mapTotal = 0;

    for (const m of REAL) {
      floorTotal += best(3, () => {
        winChanceFloor(m, 1, 5, true);
      });
      mapTotal += best(3, () => {
        dodgeMapChance(m, 1, 5, true);
      });
    }

    const n = REAL.length;
    const ceiling = (floorTotal / mapTotal) * 100;

    console.log(
      `\n  Per board, mean of ${n} real boards:\n` +
        `    winChanceFloor      ${(floorTotal / n).toFixed(2)} ms\n` +
        `    dodgeMapChance      ${(mapTotal / n).toFixed(2)} ms\n` +
        `    sharing the baseline saves at most ${ceiling.toFixed(1)}% of the map\n` +
        `    = ${(floorTotal / n).toFixed(1)} ms off ${(mapTotal / n).toFixed(0)} ms\n`,
    );

    // 26 searches in the map, 1 in the floor: the floor must be the small one.
    expect(floorTotal).toBeLessThan(mapTotal);
  });
});
