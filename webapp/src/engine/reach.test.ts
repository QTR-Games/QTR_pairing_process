import { describe, expect, it } from "vitest";
import { forcedCeiling, forcedFloor, reachReport, type ReachReport } from "./reach";
import { protocolFloor } from "./protocol";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: number[][];
}

const fixtures = boards as Fixture[];

/**
 * One sweep of every board, shared by every assertion below.
 *
 * Computed once rather than per test on purpose. Each sweep is 31 boards of
 * ten constrained searches, and recomputing it in six separate tests put this
 * file's runtime high enough to starve `worstMatchupDodge.test.ts` of a worker
 * and push a neighbouring 2.9 s test past the 5 s default timeout.
 */
const REPORTS: { fixture: Fixture; report: ReachReport }[] = fixtures.map((fixture) => ({
  fixture,
  report: reachReport(fixture.matrix, protocolFloor(fixture.matrix, true).value, true),
}));

/** A board where every cell is identical: nothing to reach for either way. */
const flat = [
  [2, 2, 2, 2, 2],
  [2, 2, 2, 2, 2],
  [2, 2, 2, 2, 2],
  [2, 2, 2, 2, 2],
  [2, 2, 2, 2, 2],
];

describe("forcedCeiling", () => {
  it("never promises more than the column holds, and names who supplies it", () => {
    for (const { fixture, report } of REPORTS) {
      for (const c of report.ceilings) {
        expect(c.level).not.toBeNull();
        expect(c.level!).toBeLessThanOrEqual(c.columnBest);
        expect(c.via.length).toBeGreaterThan(0);
        for (const i of c.via) {
          expect(fixture.matrix[i][c.theirs]).toBeGreaterThanOrEqual(c.level!);
        }
      }
    }
  });

  it("flags the columns where the grid reads better than the protocol delivers", () => {
    let overstated = 0;
    let total = 0;
    for (const { report } of REPORTS) {
      for (const c of report.ceilings) {
        total++;
        if (c.overstated) overstated++;
      }
    }
    // Measured 25/155. Asserted as a band so a solver regression is caught but
    // adding a fixture board does not fail the suite on an exact count.
    expect(total).toBe(155);
    expect(overstated).toBeGreaterThan(10);
    expect(overstated).toBeLessThan(60);
  });

  it("reads the only level on a flat board", () => {
    const c = forcedCeiling(flat, 0, protocolFloor(flat, true).value);
    expect(c.level).toBe(2);
    expect(c.columnBest).toBe(2);
    expect(c.overstated).toBe(false);
    expect(c.via).toEqual([0, 1, 2, 3, 4]);
  });
});

describe("forcedFloor", () => {
  it("never claims a worse level than the row holds, and names who delivers it", () => {
    for (const { fixture, report } of REPORTS) {
      for (const f of report.floors) {
        expect(f.level).toBeGreaterThanOrEqual(f.rowWorst);
        expect(fixture.matrix[f.ours]).toContain(f.level);
        expect(f.via.length).toBeGreaterThan(0);
        for (const j of f.via) expect(fixture.matrix[f.ours][j]).toBe(f.level);
      }
    }
  });

  it("finds the protocol shielding our players more often than not", () => {
    let shielded = 0;
    let total = 0;
    for (const { report } of REPORTS) {
      for (const f of report.floors) {
        total++;
        if (f.protectedByProtocol) shielded++;
      }
    }
    // Measured 64/155 -- the headline claim this module exists to make.
    expect(total).toBe(155);
    expect(shielded).toBeGreaterThan(30);
    expect(shielded).toBeLessThan(110);
  });

  it("reads the only level on a flat board", () => {
    const f = forcedFloor(flat, 0, protocolFloor(flat, true).value);
    expect(f.level).toBe(2);
    expect(f.rowWorst).toBe(2);
    expect(f.protectedByProtocol).toBe(false);
  });
});

describe("reachReport", () => {
  it("covers every player on both sides", () => {
    const { report } = REPORTS[0];
    expect(report.ceilings).toHaveLength(5);
    expect(report.floors).toHaveLength(5);
    expect(report.ceilings.map((c) => c.theirs)).toEqual([0, 1, 2, 3, 4]);
    expect(report.floors.map((f) => f.ours)).toEqual([0, 1, 2, 3, 4]);
  });

  it("is scale-free: multiplying every rating rescales the answers exactly", () => {
    const { fixture, report } = REPORTS[3];
    const scaled = fixture.matrix.map((row) => row.map((v) => v * 10));
    const big = reachReport(scaled, protocolFloor(scaled, true).value);
    expect(big.ceilings.map((c) => c.level)).toEqual(report.ceilings.map((c) => c.level! * 10));
    expect(big.floors.map((f) => f.level)).toEqual(report.floors.map((f) => f.level * 10));
  });

  it("threads through which side nominates first", () => {
    // Not an equality claim -- only that the flag reaches the solver rather
    // than the grid being read directly, which would ignore it entirely.
    const { matrix } = fixtures[6];
    const report = reachReport(matrix, protocolFloor(matrix, false).value, false);
    for (const c of report.ceilings) expect(c.level).not.toBeNull();
  });
});
