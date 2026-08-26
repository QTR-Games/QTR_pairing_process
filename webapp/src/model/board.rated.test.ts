/*
  The flat board, and why it used to disappear.

  Ratings are stored as fractions, and a mid rating is exactly 0.5 -- 3 on the
  1-5 scale, amber on the stoplight. An untouched board is seeded with 0.5 in
  every cell. So "every matchup is dead even" and "nobody has opened this yet"
  had the same representation, and `isRated` could only ever answer one of them.

  It answered "untouched", which meant App.tsx's autosave guard
  (`board.opponent || isRated(board)`) dropped the board on the floor. Rating a
  whole grid amber and then closing the app lost the lot.

  These tests pin the fix and, just as importantly, pin the fallback: boards
  saved before the `touched` flag existed still have to read correctly.
*/

import { describe, expect, it } from "vitest";
import { emptyBoard, isRated, setRating, type Board } from "./board";
import { scaleById } from "./scale";

const five = scaleById("five");
const stoplight = scaleById("stoplight");

/** Rate every cell the same, the way a first pass across a grid actually goes. */
function rateAll(board: Board, value: number, scale = five): Board {
  let next = board;
  for (let i = 0; i < 5; i++) {
    for (let j = 0; j < 5; j++) next = setRating(next, i, j, value, scale);
  }
  return next;
}

describe("isRated", () => {
  it("still says no to a board nobody has touched", () => {
    expect(isRated(emptyBoard())).toBe(false);
  });

  it("counts a board rated dead even on 1-5 as rated", () => {
    const board = rateAll(emptyBoard(), 3);
    // Every fraction is 0.5, exactly as an untouched board -- the flag is the
    // only thing telling these apart.
    expect(board.fractions.every((r) => r.every((f) => f === 0.5))).toBe(true);
    expect(isRated(board)).toBe(true);
  });

  it("counts an all-amber stoplight board as rated", () => {
    // The likelier version of the same bug: amber is the middle of three, so a
    // cautious first pass across the grid produced a board that vanished.
    const board = rateAll(emptyBoard("stoplight"), 2, stoplight);
    expect(isRated(board)).toBe(true);
  });

  it("survives a rating that is set and then flattened back to even", () => {
    const board = setRating(rateAll(emptyBoard(), 3), 0, 0, 3, five);
    expect(isRated(board)).toBe(true);
  });

  it("reads a legacy board with no flag from its fractions", () => {
    // Boards already in localStorage predate `touched`. A rated one must still
    // read as rated without any migration step.
    const legacy = { ...rateAll(emptyBoard(), 5), touched: undefined };
    expect(legacy.touched).toBeUndefined();
    expect(isRated(legacy)).toBe(true);
  });

  it("leaves the legacy flat board exactly as it behaved before", () => {
    // No pretending this is fixed retroactively: a flat board saved before the
    // flag has nothing to distinguish it, and guessing would be worse.
    const legacy = { ...rateAll(emptyBoard(), 3), touched: undefined };
    expect(isRated(legacy)).toBe(false);
  });

  it("keeps saying yes to an ordinary lopsided board", () => {
    expect(isRated(setRating(emptyBoard(), 2, 3, 5, five))).toBe(true);
  });
});
