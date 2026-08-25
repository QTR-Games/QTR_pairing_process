/*
  Guards the two claims the exposure overlay is built on, and the one it is
  built AROUND.

  Asserted as bands rather than exact counts on purpose: a change to the solver
  should fail this file, but adding a board to the fixture set should not. The
  bands are wide enough to absorb a few new boards and narrow enough that a
  degeneracy would break them.

  The frontier assertion is the unusual one. It asserts that a shipped engine
  structure is DEGENERATE -- that decisionReport.frontier holds a single
  distinct (floor, ceiling) offer on the overwhelming majority of real boards.
  That is why the desktop overlay draws cellOutlooks instead. If someone later
  changes the dominance rule and the frontier starts carrying real trade-offs,
  this test should fail loudly, because at that point the overlay is showing the
  wrong structure and the decision to skip the frontier needs revisiting.
*/
import { describe, expect, it } from "vitest";
import { cellOutlooks, decisionReport, evenThreshold } from "./boardAnalysis";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  matrix: number[][];
}

const fixtures = (boards as Fixture[]).filter((b) => b.matrix.length === 5);
const EPS = 1e-9;

function exposure(matrix: number[][]) {
  const map = cellOutlooks(matrix, evenThreshold(matrix.length, 1, 5));
  const floors = [...map.values()].map((o) => o.floor);
  const best = Math.max(...floors);
  return {
    spread: best - Math.min(...floors),
    tiedAtBest: floors.filter((f) => Math.abs(f - best) < EPS).length,
    costlyByAPoint: floors.filter((f) => best - f >= 1 - EPS).length,
    count: floors.length,
  };
}

describe("cell exposure map", () => {
  it("has a real spread on every board, so the overlay is never blank", () => {
    expect(fixtures.length).toBeGreaterThan(20);
    for (const { matrix } of fixtures) {
      const e = exposure(matrix);
      expect(e.count).toBe(25);
      // Measured: mean 2.61, range 1.00 to 4.00, flat on 0 of 31.
      expect(e.spread).toBeGreaterThan(0);
    }
  });

  it("keeps the tied-best set small enough to read as a shortlist", () => {
    const tied = fixtures.map((f) => exposure(f.matrix).tiedAtBest);
    const mean = tied.reduce((a, b) => a + b, 0) / tied.length;
    // Measured mean 2.87 of 25. If this ever approached 25 the overlay would be
    // telling you every option is fine, which would make it worthless.
    expect(mean).toBeGreaterThan(1);
    expect(mean).toBeLessThan(8);
    expect(Math.min(...tied)).toBeGreaterThanOrEqual(1);
  });

  it("shows that most of the board costs a point or more", () => {
    const costly = fixtures.map((f) => exposure(f.matrix).costlyByAPoint);
    const mean = costly.reduce((a, b) => a + b, 0) / costly.length;
    // Measured mean 22.13 of 25. This is the whole justification for the
    // overlay: the board is mostly mistakes and nothing else says so.
    expect(mean).toBeGreaterThan(15);
    expect(mean).toBeLessThan(25);
  });

  it("confirms the Pareto frontier is degenerate, which is why it is not drawn", () => {
    let single = 0;
    for (const { matrix } of fixtures) {
      const rep = decisionReport(matrix, evenThreshold(matrix.length, 1, 5));
      const distinct = new Set(
        rep.frontier.map((c) => `${c.outlook.floor.toFixed(6)}|${c.outlook.ceiling.toFixed(6)}`),
      );
      if (distinct.size === 1) single++;
    }
    // Measured 30 of 31. A frontier of ten cells is ten cells holding the same
    // value; it is a tie, not a choice.
    expect(single / fixtures.length).toBeGreaterThan(0.8);
  });
});
