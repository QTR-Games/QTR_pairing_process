/**
 * Avoidance is a claim about the protocol, so it is tested against the protocol
 * solver rather than against hand-computed numbers. Two properties do most of
 * the work:
 *
 *   - With nothing forbidden, it must reproduce `protocolFloor` exactly. If it
 *     ever does not, the two searches have drifted and every price is suspect.
 *   - On a full board, any single cell must be avoidable. That is the structural
 *     result measured over 45 saved boards; the 31 fixtures here re-derive it in
 *     CI so a change to the turn-taking rules cannot silently repeal it.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { protocolFloor } from "./protocol";
import {
  type Cell,
  avoidingFloor,
  dodgeMap,
  forbidCells,
  priceCells,
  pricePair,
} from "./avoidance";

const FIXTURES = boards as { opponent: string; matrix: number[][] }[];

const worstCells = (matrix: Matrix, count: number): Cell[] => {
  const cells: { cell: Cell; rating: number }[] = [];
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      cells.push({ cell: { ours: i, theirs: j }, rating: matrix[i][j] });
    }
  }
  cells.sort((a, b) => a.rating - b.rating);
  return cells.slice(0, count).map((c) => c.cell);
};

describe("avoidance agrees with the unconstrained solver", () => {
  it.each([true, false])("reproduces protocolFloor with nothing forbidden (weOpen=%s)", (weOpen) => {
    for (const b of FIXTURES) {
      expect(avoidingFloor(b.matrix, 0, weOpen)).toBeCloseTo(
        protocolFloor(b.matrix, weOpen).value,
        9,
      );
    }
  });

  it("never reports a constrained total above the unconstrained one", () => {
    for (const b of FIXTURES) {
      const base = protocolFloor(b.matrix, true).value;
      for (const cell of worstCells(b.matrix, 3)) {
        const { avoided } = priceCells(b.matrix, [cell], base, true);
        if (avoided !== null) expect(avoided).toBeLessThanOrEqual(base + 1e-9);
      }
    }
  });
});

describe("the avoidability property", () => {
  it.each([true, false])("can always dodge any single cell on a full board (weOpen=%s)", (weOpen) => {
    for (const b of FIXTURES) {
      const n = b.matrix.length;
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          const value = avoidingFloor(b.matrix, forbidCells([{ ours: i, theirs: j }], n), weOpen);
          expect(value, `${b.opponent} cell ${i},${j} weOpen=${weOpen}`).not.toBeNull();
        }
      }
    }
  });

  it("prices every dodge non-negatively and orders them cheapest first", () => {
    for (const b of FIXTURES) {
      const base = protocolFloor(b.matrix, true).value;
      const map = dodgeMap(b.matrix, base, true);
      expect(map).toHaveLength(b.matrix.length * b.matrix.length);
      let previous = -Infinity;
      for (const entry of map) {
        expect(entry.price).not.toBeNull();
        expect(entry.price!).toBeGreaterThanOrEqual(-1e-9);
        expect(entry.price!).toBeGreaterThanOrEqual(previous - 1e-9);
        previous = entry.price!;
        expect(entry.free).toBe(entry.price! < 1e-9);
      }
    }
  });
});

describe("avoidance does not compose", () => {
  it("finds boards where each of two cells is dodgeable but the pair is not", () => {
    let bothDodgeable = 0;
    let pairImpossible = 0;

    for (const b of FIXTURES) {
      const base = protocolFloor(b.matrix, true).value;
      const [a, second] = worstCells(b.matrix, 2);
      expect(priceCells(b.matrix, [a], base, true).avoided).not.toBeNull();
      expect(priceCells(b.matrix, [second], base, true).avoided).not.toBeNull();

      const pair = pricePair(b.matrix, a, second, base, true);
      if (pair.avoided === null) pairImpossible++;
      else bothDodgeable++;
    }

    // Both regimes must be represented, otherwise the measurement that
    // motivated this module is not reproduced by the fixtures.
    expect(pairImpossible).toBeGreaterThan(0);
    expect(bothDodgeable).toBeGreaterThan(0);
  });

  it("never prices a pair below either of its parts", () => {
    for (const b of FIXTURES) {
      const base = protocolFloor(b.matrix, true).value;
      const [a, second] = worstCells(b.matrix, 2);
      const pair = pricePair(b.matrix, a, second, base, true);
      if (pair.price === null) continue;
      for (const single of [a, second]) {
        const one = priceCells(b.matrix, [single], base, true);
        expect(pair.price).toBeGreaterThanOrEqual(one.price! - 1e-9);
      }
    }
  });
});

describe("scale independence", () => {
  it("prices in the board's own units, so 1-3, 1-5 and 1-10 all work", () => {
    for (const b of FIXTURES.slice(0, 8)) {
      const base = protocolFloor(b.matrix, true).value;
      const [worst] = worstCells(b.matrix, 1);
      const one = priceCells(b.matrix, [worst], base, true);

      const doubled = b.matrix.map((row) => row.map((x) => x * 2));
      const doubledBase = protocolFloor(doubled, true).value;
      const two = priceCells(doubled, [worst], doubledBase, true);

      expect(two.price!).toBeCloseTo(one.price! * 2, 9);
      expect(two.free).toBe(one.free);
    }
  });

  it("is unaffected by adding a constant to every rating", () => {
    for (const b of FIXTURES.slice(0, 8)) {
      const base = protocolFloor(b.matrix, true).value;
      const [worst] = worstCells(b.matrix, 1);
      const one = priceCells(b.matrix, [worst], base, true);

      const shifted = b.matrix.map((row) => row.map((x) => x + 7));
      const shiftedBase = protocolFloor(shifted, true).value;
      const two = priceCells(shifted, [worst], shiftedBase, true);

      expect(two.price!).toBeCloseTo(one.price!, 9);
    }
  });
});
