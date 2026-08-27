/*
  activeProtectPriority is the one gate between a stored protect-first choice and
  everything that reads it (the grid marker, the radio's "selected" state). The
  raw `protectPriority` field is never trusted directly because a board outlives
  the exposure that motivated the choice: re-rate it and the chosen player can
  stop being exposed, or the field can carry a garbage index from an older save.

  These pin the two halves of "still a real decision": in range AND currently
  exposed. Miss either and the reader must see "no preference", so a stale pick
  is inert rather than silently marking the wrong row.
*/

import { describe, expect, it } from "vitest";
import { activeProtectPriority, emptyBoard, type Board } from "./board";

/** A board whose only interesting field is the stored choice. */
function withChoice(choice: number | null | undefined): Board {
  const b = emptyBoard();
  return choice === undefined ? b : { ...b, protectPriority: choice };
}

describe("activeProtectPriority", () => {
  it("reads absent as no preference", () => {
    expect(activeProtectPriority(withChoice(undefined), [0, 1, 2])).toBeNull();
  });

  it("reads an explicit null as no preference", () => {
    expect(activeProtectPriority(withChoice(null), [0, 1, 2])).toBeNull();
  });

  it("returns the index when it is in range and that player is exposed", () => {
    expect(activeProtectPriority(withChoice(2), [0, 2, 4])).toBe(2);
  });

  it("returns null when the chosen player is no longer exposed", () => {
    // The index is a valid roster slot, but the re-rating that removed them from
    // the exposed set is exactly the case a raw read would get wrong.
    expect(activeProtectPriority(withChoice(2), [0, 1, 3])).toBeNull();
  });

  it("returns null for an out-of-range index", () => {
    // Five players, so 5 is one past the end. A stale save must not index off
    // the roster.
    expect(activeProtectPriority(withChoice(5), [0, 1, 2, 3, 4, 5])).toBeNull();
  });

  it("returns null for a negative index", () => {
    expect(activeProtectPriority(withChoice(-1), [-1, 0, 1])).toBeNull();
  });

  it("returns null for a non-integer index", () => {
    expect(activeProtectPriority(withChoice(1.5), [1.5, 0, 1])).toBeNull();
  });

  it("accepts an empty exposed set as no preference", () => {
    expect(activeProtectPriority(withChoice(0), [])).toBeNull();
  });

  it("works with a Set, not only an array", () => {
    expect(activeProtectPriority(withChoice(3), new Set([1, 3]))).toBe(3);
    expect(activeProtectPriority(withChoice(3), new Set([1, 2]))).toBeNull();
  });
});
