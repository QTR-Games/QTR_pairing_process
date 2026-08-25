/**
 * Step 1 of the pairing protocol: which side to take after winning the dice-off.
 *
 * These tests pin the contract rather than the advice. The advice is measured
 * (`measure.openOrReceive.test.ts`, `measure.openTheorem.test.ts`) and is a
 * strong default with known exceptions, so asserting "always receive" here
 * would be asserting something the measurement already refuted.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { openingChoice, protocolFloor } from "./protocol";
import type { Matrix } from "./boardAnalysis";

const FIXTURES = (boards as { opponent: string; matrix: number[][] }[]).slice(0, 8);

describe("openingChoice", () => {
  it("reports both floors and picks the larger", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const c = openingChoice(matrix);
      expect(c.openValue, opponent).toBeCloseTo(protocolFloor(matrix, true).value, 9);
      expect(c.receiveValue, opponent).toBeCloseTo(protocolFloor(matrix, false).value, 9);
      expect(c.weOpen, opponent).toBe(c.openValue > c.receiveValue);
    }
  });

  it("reports a non-negative gain equal to the gap between the two", () => {
    for (const { opponent, matrix } of FIXTURES) {
      const c = openingChoice(matrix);
      expect(c.gain, opponent).toBeGreaterThanOrEqual(0);
      expect(c.gain, opponent).toBeCloseTo(Math.abs(c.openValue - c.receiveValue), 9);
    }
  });

  it("calls it a tie rather than picking a side when the floors match", () => {
    // Every cell equal: nothing anyone chooses can change the total.
    const flat: Matrix = Array.from({ length: 5 }, () => [3, 3, 3, 3, 3]);
    const c = openingChoice(flat);
    expect(c.gain).toBeCloseTo(0, 9);
    expect(c.weOpen).toBe(false);
  });

  /**
   * The measured default, stated as a test so a regression in the protocol
   * search is caught here rather than at an event. Receiving is at least as
   * good as opening on all 31 real boards -- and this asserts exactly that,
   * not that it holds universally, because at n=4 it demonstrably does not.
   */
  it("never prefers opening on a real board", () => {
    for (const { opponent, matrix } of boards as { opponent: string; matrix: number[][] }[]) {
      expect(openingChoice(matrix).weOpen, opponent).toBe(false);
    }
  });

  /**
   * And the counterexample, pinned so the code is never simplified into
   * hardcoding "always receive". Found by `measure.openTheorem.test.ts`; this
   * is a 4v4 board, which is not a WTC format, but the engine takes a matrix
   * rather than a format.
   */
  it("does prefer opening on the known n=4 counterexample", () => {
    const witness: Matrix = [
      [1, 4, 1, 5],
      [4, 1, 1, 1],
      [4, 5, 2, 1],
      [1, 1, 5, 3],
    ];
    const c = openingChoice(witness);
    expect(c.weOpen).toBe(true);
    expect(c.gain).toBeCloseTo(5, 9);
  });
});
