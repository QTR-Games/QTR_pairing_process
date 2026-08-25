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
   * not that it holds universally, because the counterexamples below are
   * 5v5 boards on real scales.
   */
  it("never prefers opening on a real board", () => {
    for (const { opponent, matrix } of boards as { opponent: string; matrix: number[][] }[]) {
      expect(openingChoice(matrix).weOpen, opponent).toBe(false);
    }
  });

  /**
   * And the counterexample, pinned so the code is never simplified into
   * hardcoding "always receive". Found by `measure.openTheorem.test.ts` at
   * 5v5 on the 1-10 scale -- the exact format and scale being used at the
   * event, not a hypothetical board size.
   */
  it("does prefer opening on the known 5v5 counterexample", () => {
    const witness: Matrix = [
      [5, 2, 10, 2, 5],
      [10, 1, 1, 5, 6],
      [8, 2, 5, 9, 6],
      [4, 8, 2, 1, 6],
      [1, 1, 9, 1, 5],
    ];
    const c = openingChoice(witness);
    expect(c.weOpen).toBe(true);
    expect(c.gain).toBeCloseTo(1, 9);
  });

  /**
   * A compressed scale is where ties concentrate, and ties are where the
   * choice stops being forced. Pinned separately because a team who rate
   * everything 4 or 5 are the most likely to hit one of these in practice.
   */
  it("does prefer opening on the compressed-scale counterexample", () => {
    const witness: Matrix = [
      [4, 4, 5, 4, 5],
      [5, 4, 4, 5, 5],
      [5, 4, 4, 5, 5],
      [4, 4, 4, 4, 5],
      [4, 5, 5, 4, 5],
    ];
    const c = openingChoice(witness);
    expect(c.weOpen).toBe(true);
    expect(c.gain).toBeCloseTo(1, 9);
  });
});
