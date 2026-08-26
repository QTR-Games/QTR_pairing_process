/*
  The frontier is degenerate. Is the 25-cell outlook map?

  measure.frontier established that decisionReport.frontier collapses to a
  single distinct (floor, ceiling) offer on 30 of 31 real boards. A Pareto
  overlay would therefore be a UI for a one-element set, which is the same
  dead end the pin family turned out to be.

  cellOutlooks is the structure the frontier is derived from, and it is not
  obviously dead for the same reason. The frontier answers "which cells are
  non-dominated", which is nearly always one. The map answers a different and
  possibly better question: "what does each of the 25 choices actually cost
  me?" Even when one cell wins outright, the SHAPE of the penalty across the
  other 24 is information the app has never shown -- it is the difference
  between "this is best" and "this is best, and these four are nearly as good
  while these six are disasters".

  That is only worth drawing if the 25 cells actually differ. If every cell
  produces the same floor, there is nothing to see.

  Measured here:
    1. spread of guaranteed floor across all 25 cells, per board
    2. how many cells tie the best floor (if it is 25, the choice is free;
       if it is 1, the choice is everything)
    3. how many cells are outright catastrophic -- a full point or more below
       the best available floor
    4. cost

  Run with:
    $env:QTR_MEASURE=1; npx vitest run src/engine/measure.exposure.test.ts --disable-console-intercept
*/
import { describe, it } from "vitest";
import { cellOutlooks, evenThreshold } from "./boardAnalysis";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  matrix: number[][];
}

describe.skipIf(!process.env.QTR_MEASURE)("cell exposure map", () => {
  it("measures whether the 25 cells differ enough to be worth drawing", () => {
    const fixtures = (boards as Fixture[]).filter((b) => b.matrix.length === 5);

    for (const f of fixtures.slice(0, 3)) cellOutlooks(f.matrix, evenThreshold(5, 1, 5));

    const floorSpreads: number[] = [];
    const ceilingSpreads: number[] = [];
    const tiedAtBest: number[] = [];
    const disasters: number[] = [];
    let totalMs = 0;
    let worstMs = 0;
    let flatBoards = 0;

    for (const { matrix } of fixtures) {
      const tau = evenThreshold(matrix.length, 1, 5);
      const t0 = performance.now();
      const map = cellOutlooks(matrix, tau);
      const dt = performance.now() - t0;
      totalMs += dt;
      worstMs = Math.max(worstMs, dt);

      const floors = [...map.values()].map((o) => o.floor);
      const ceilings = [...map.values()].map((o) => o.ceiling);
      const bestFloor = Math.max(...floors);
      const worstFloor = Math.min(...floors);

      floorSpreads.push(bestFloor - worstFloor);
      ceilingSpreads.push(Math.max(...ceilings) - Math.min(...ceilings));
      tiedAtBest.push(floors.filter((f) => Math.abs(f - bestFloor) < 1e-9).length);
      disasters.push(floors.filter((f) => bestFloor - f >= 1 - 1e-9).length);
      if (bestFloor - worstFloor < 1e-9) flatBoards++;
    }

    const n = fixtures.length;
    const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
    const hist = (a: number[]) => {
      const m = new Map<number, number>();
      for (const v of a) m.set(v, (m.get(v) ?? 0) + 1);
      return [...m.entries()].sort((x, y) => x[0] - y[0]).map(([k, v]) => `${k}:${v}`).join("  ");
    };

    console.log(`
  boards                                    ${n}

  spread of guaranteed floor across 25 cells
    mean                                    ${mean(floorSpreads).toFixed(2)} pts
    min / max                               ${Math.min(...floorSpreads).toFixed(2)} / ${Math.max(...floorSpreads).toFixed(2)}
    boards where every cell is identical    ${flatBoards}/${n}

  spread of reachable ceiling across 25 cells
    mean                                    ${mean(ceilingSpreads).toFixed(2)} pts

  how many of the 25 tie the best floor
    histogram (count:boards)                ${hist(tiedAtBest)}
    mean                                    ${mean(tiedAtBest).toFixed(2)} of 25

  how many cost a full point or more
    histogram (count:boards)                ${hist(disasters)}
    mean                                    ${mean(disasters).toFixed(2)} of 25

  cost
    cellOutlooks mean per board             ${(totalMs / n).toFixed(2)} ms
    cellOutlooks worst board                ${worstMs.toFixed(2)} ms
`);
  }, 120_000);
});
