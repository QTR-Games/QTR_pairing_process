/**
 * Table tracking is metadata over a pairing the solver has already locked in --
 * it must never move `banked`, the pools, or which pairing is at a given index.
 * These tests pin that contract directly, independent of any UI that calls it.
 */
import { describe, expect, it } from "vitest";
import type { Matrix } from "./boardAnalysis";
import { commitPairing, newRound, setCommittedTable } from "./live";

const matrix: Matrix = [
  [0.6, 0.4],
  [0.3, 0.7],
];

describe("commitPairing", () => {
  it("records a new pairing with no table yet", () => {
    const s = commitPairing(matrix, newRound(2, true), 0, 1, null, null);
    expect(s.committed).toEqual([{ ours: 0, theirs: 1, value: matrix[0][1], table: null }]);
  });
});

describe("setCommittedTable", () => {
  it("sets the table on the named entry, leaving the rest of the state alone", () => {
    const committed = commitPairing(matrix, newRound(2, true), 0, 1, null, null);
    const tabled = setCommittedTable(committed, 0, "5");

    expect(tabled.committed).toEqual([{ ours: 0, theirs: 1, value: matrix[0][1], table: "5" }]);
    expect(tabled.banked).toBe(committed.banked);
    expect(tabled.ourPool).toBe(committed.ourPool);
    expect(tabled.theirPool).toBe(committed.theirPool);
  });

  it("can clear a table back to null", () => {
    const committed = commitPairing(matrix, newRound(2, true), 0, 1, null, null);
    const tabled = setCommittedTable(committed, 0, "5");
    const cleared = setCommittedTable(tabled, 0, null);

    expect(cleared.committed[0].table).toBeNull();
  });

  it("leaves the state untouched for an out-of-range index", () => {
    const s = newRound(2, true);
    expect(setCommittedTable(s, 0, "5")).toEqual(s);
    expect(setCommittedTable(s, -1, "5")).toEqual(s);
  });

  it("only touches the named entry when several pairings are committed", () => {
    let s = commitPairing(matrix, newRound(2, true), 0, 1, null, null);
    s = { ...s, ourPool: 0, theirPool: 0, committed: [...s.committed, { ours: 1, theirs: 0, value: matrix[1][0], table: null }] };

    const tabled = setCommittedTable(s, 1, "9");
    expect(tabled.committed[0].table).toBeNull();
    expect(tabled.committed[1].table).toBe("9");
  });
});
