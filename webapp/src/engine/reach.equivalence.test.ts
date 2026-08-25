/**
 * The cheap rule in `reach.ts` must keep agreeing with the search it replaced.
 *
 * `forcedCeiling` and `forcedFloor` were collapsed from a constrained
 * adversarial search into a sort and a count, on the strength of a measurement
 * over 31 boards rather than a proof. That is a good trade only while the
 * measurement holds. This file re-checks it on every run.
 *
 * Coverage is the full sweep: 31 boards x 5 columns x 2 dice-off orientations
 * for ceilings, and the same for floors, so 620 observations. It runs in the
 * default suite rather than behind `QTR_MEASURE` -- deliberately, and unlike
 * the `measure.*` harnesses. Those report numbers nobody has to act on. This
 * one is the safety argument for the collapse: if a future board breaks the
 * equivalence, the suite has to fail loudly instead of the app quietly showing
 * a reachable level that is not reachable.
 */

import { describe, expect, it } from "vitest";
import {
  forcedCeiling,
  forcedCeilingBySearch,
  forcedFloor,
  forcedFloorBySearch,
} from "./reach";
import { protocolFloor } from "./protocol";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  matrix: number[][];
}

const fixtures = boards as Fixture[];
const ORIENTATIONS = [true, false] as const;

/**
 * Generous on purpose. The whole sweep is roughly 700 ms of solver, well inside
 * the 5 s default, but this file must never be the marginal one that fails
 * under parallel load the way `worstMatchupDodge.test.ts` did.
 */
const TIMEOUT = { timeout: 120_000 };

describe("the cheap reach rule agrees with the search it replaced", () => {
  it("matches forcedCeilingBySearch on every column, both orientations", TIMEOUT, () => {
    let checked = 0;

    for (const ourTeamFirst of ORIENTATIONS) {
      for (const { opponent, matrix } of fixtures) {
        const base = protocolFloor(matrix, ourTeamFirst).value;

        for (let theirs = 0; theirs < matrix.length; theirs++) {
          const cheap = forcedCeiling(matrix, theirs, base, ourTeamFirst);
          const oracle = forcedCeilingBySearch(matrix, theirs, base, ourTeamFirst);
          const where = `${opponent} col ${theirs} ourTeamFirst=${ourTeamFirst}`;

          expect(cheap.level, `level: ${where}`).toBe(oracle.level);
          expect(cheap.via, `via: ${where}`).toEqual(oracle.via);
          expect(cheap.overstated, `overstated: ${where}`).toBe(oracle.overstated);
          expect(cheap.columnBest, `columnBest: ${where}`).toBe(oracle.columnBest);
          checked++;
        }
      }
    }

    expect(checked).toBe(fixtures.length * 5 * ORIENTATIONS.length);
  });

  it("matches forcedFloorBySearch on every row, both orientations", TIMEOUT, () => {
    let checked = 0;

    for (const ourTeamFirst of ORIENTATIONS) {
      for (const { opponent, matrix } of fixtures) {
        const base = protocolFloor(matrix, ourTeamFirst).value;

        for (let ours = 0; ours < matrix.length; ours++) {
          const cheap = forcedFloor(matrix, ours, base, ourTeamFirst);
          const oracle = forcedFloorBySearch(matrix, ours, base, ourTeamFirst);
          const where = `${opponent} row ${ours} ourTeamFirst=${ourTeamFirst}`;

          expect(cheap.level, `level: ${where}`).toBe(oracle.level);
          expect(cheap.via, `via: ${where}`).toEqual(oracle.via);
          expect(
            cheap.protectedByProtocol,
            `protectedByProtocol: ${where}`,
          ).toBe(oracle.protectedByProtocol);
          expect(cheap.rowWorst, `rowWorst: ${where}`).toBe(oracle.rowWorst);
          checked++;
        }
      }
    }

    expect(checked).toBe(fixtures.length * 5 * ORIENTATIONS.length);
  });
});

describe("the tie structure at the extreme is the whole rule", () => {
  /**
   * The collapse is only legible if the reason is stated as a test too. A
   * unique extreme is one cell, one cell is always dodgeable, so the level
   * moves exactly one rung; a tied extreme cannot be dodged and does not move.
   */
  it("moves the level exactly when the extreme is unique", TIMEOUT, () => {
    for (const { opponent, matrix } of fixtures) {
      for (let j = 0; j < matrix.length; j++) {
        const column = matrix.map((row) => row[j]);
        const levels = [...new Set(column)].sort((a, b) => b - a);
        const unique = column.filter((v) => v === levels[0]).length === 1;
        const c = forcedCeiling(matrix, j);

        expect(c.overstated, `${opponent} col ${j}`).toBe(unique);
        expect(c.level, `${opponent} col ${j}`).toBe(unique ? levels[1] : levels[0]);
      }

      for (let i = 0; i < matrix.length; i++) {
        const row = matrix[i];
        const levels = [...new Set(row)].sort((a, b) => a - b);
        const unique = row.filter((v) => v === levels[0]).length === 1;
        const f = forcedFloor(matrix, i);

        expect(f.protectedByProtocol, `${opponent} row ${i}`).toBe(unique);
        expect(f.level, `${opponent} row ${i}`).toBe(unique ? levels[1] : levels[0]);
      }
    }
  });

  it("is independent of who nominates first", TIMEOUT, () => {
    for (const { opponent, matrix } of fixtures) {
      const first = protocolFloor(matrix, true).value;
      const second = protocolFloor(matrix, false).value;

      for (let i = 0; i < matrix.length; i++) {
        expect(forcedCeiling(matrix, i, first, true).level, `${opponent} col ${i}`).toBe(
          forcedCeiling(matrix, i, second, false).level,
        );
        expect(forcedFloor(matrix, i, first, true).level, `${opponent} row ${i}`).toBe(
          forcedFloor(matrix, i, second, false).level,
        );
      }
    }
  });
});
