/*
  Is the Pareto frontier small enough to be worth drawing?

  `decisionReport.frontier` is the set of first pairings that no other pairing
  beats on both bounds at once -- better guaranteed floor AND better reachable
  ceiling. It is computed on every board and has never been rendered.

  The case for showing it is the "smart sort" problem. Smart sort ranks all 25
  cells by one aggregate and hands back the single winner. That is only honest
  if the cells form a total order, and they do not: a cell can protect the floor
  while giving up ceiling, and one number cannot express that trade. The
  frontier is exactly the set where the trade is real.

  But it is only worth screen space if it is SMALL. Three cells out of
  twenty-five is a shortlist. Twenty out of twenty-five is wallpaper, and
  drawing it would be worse than saying nothing.

  Three questions:

    1. size. How many of the 25 cells survive domination, per board?
    2. cost. cellOutlooks is 25 constrained solves of a 4x4. If it is anywhere
       near the 293 ms dodge map it needs a switch, not an always-on overlay.
    3. does it disagree with smart sort? If the ceiling-ranked winner is always
       also the floor-ranked winner, the frontier tells you nothing you did not
       already have and this whole idea is dead.

  Run with:
    $env:QTR_MEASURE=1; npx vitest run src/engine/measure.frontier.test.ts --disable-console-intercept
*/
import { describe, it } from "vitest";
import { decisionReport, cellOutlooks, evenThreshold } from "./boardAnalysis";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  matrix: number[][];
}

describe.skipIf(!process.env.QTR_MEASURE)("pareto frontier", () => {
  it("measures frontier size, cost, and whether it disagrees with a single ranking", () => {
    const fixtures = (boards as Fixture[]).filter((b) => b.matrix.length === 5);

    // Warm the JIT.
    for (const f of fixtures.slice(0, 3)) {
      decisionReport(f.matrix, evenThreshold(5, 1, 5));
    }

    const sizes: number[] = [];
    const distinctSizes: number[] = [];
    let totalMs = 0;
    let worstMs = 0;
    let disagreements = 0;
    let choiceMattered = 0;
    const floorSpreads: number[] = [];

    for (const { matrix } of fixtures) {
      const tau = evenThreshold(matrix.length, 1, 5);

      const t0 = performance.now();
      const rep = decisionReport(matrix, tau);
      const dt = performance.now() - t0;
      totalMs += dt;
      worstMs = Math.max(worstMs, dt);

      sizes.push(rep.frontier.length);
      if (rep.choiceMatters) choiceMattered++;

      // How many GENUINELY DIFFERENT offers are on the frontier? Two cells with
      // the same (floor, ceiling) cannot dominate each other, so both survive --
      // but they are the same offer wearing two names, not a trade-off. Only
      // distinct pairs represent an actual decision.
      const distinct = new Set(
        rep.frontier.map((c) => `${c.outlook.floor.toFixed(6)}|${c.outlook.ceiling.toFixed(6)}`),
      );
      distinctSizes.push(distinct.size);

      // Does ranking by ceiling alone pick a different cell than ranking by
      // floor alone? If it never does, one number would have been enough.
      const byCeiling = [...rep.frontier].sort(
        (a, b) => b.outlook.ceiling - a.outlook.ceiling || b.outlook.floor - a.outlook.floor,
      )[0];
      const byFloor = [...rep.frontier].sort(
        (a, b) => b.outlook.floor - a.outlook.floor || b.outlook.ceiling - a.outlook.ceiling,
      )[0];
      if (byCeiling.ours !== byFloor.ours || byCeiling.theirs !== byFloor.theirs) {
        disagreements++;
        floorSpreads.push(byFloor.outlook.floor - byCeiling.outlook.floor);
      }
    }

    // Separately, the raw cost of the 25-cell outlook map on its own.
    let mapMs = 0;
    for (const { matrix } of fixtures) {
      const tau = evenThreshold(matrix.length, 1, 5);
      const t0 = performance.now();
      cellOutlooks(matrix, tau);
      mapMs += performance.now() - t0;
    }

    const n = fixtures.length;
    const hist = new Map<number, number>();
    for (const s of sizes) hist.set(s, (hist.get(s) ?? 0) + 1);
    const histStr = [...hist.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([k, v]) => `${k}:${v}`)
      .join("  ");
    const meanSize = sizes.reduce((a, b) => a + b, 0) / n;
    const dHist = new Map<number, number>();
    for (const s of distinctSizes) dHist.set(s, (dHist.get(s) ?? 0) + 1);
    const dHistStr = [...dHist.entries()].sort((a, b) => a[0] - b[0]).map(([k, v]) => `${k}:${v}`).join("  ");
    const meanDistinct = distinctSizes.reduce((a, b) => a + b, 0) / n;
    const meanSpread = floorSpreads.length
      ? floorSpreads.reduce((a, b) => a + b, 0) / floorSpreads.length
      : 0;

    console.log(`
  boards                                    ${n}

  frontier size, out of 25 cells
    histogram (size:boards)                 ${histStr}
    mean                                    ${meanSize.toFixed(2)}
    min / max                               ${Math.min(...sizes)} / ${Math.max(...sizes)}

  DISTINCT (floor, ceiling) offers on the frontier
    histogram (distinct:boards)             ${dHistStr}
    mean                                    ${meanDistinct.toFixed(2)}
    boards offering a real choice (>1)      ${distinctSizes.filter((s) => s > 1).length}/${n}

  cost
    decisionReport, mean per board          ${(totalMs / n).toFixed(2)} ms
    decisionReport, worst board             ${worstMs.toFixed(2)} ms
    cellOutlooks alone, mean per board      ${(mapMs / n).toFixed(2)} ms

  does one ranking suffice?
    boards where choice matters             ${choiceMattered}/${n}
    ceiling-best differs from floor-best    ${disagreements}/${n}
    mean floor given up by taking ceiling   ${meanSpread.toFixed(2)} pts
`);
  }, 120_000);
});
