// @vitest-environment jsdom
/**
 * The dice-off line, on the screen rather than in the engine.
 *
 * `measure.diceoff` established the fact this covers: across the 31 saved event
 * boards the gap between opening and receiving takes exactly one non-zero
 * value, 1.000 points, and is exactly zero on 13 of them. So the free case is
 * not an edge case, it is more than a third of real boards.
 *
 * Until now the panel rendered that insight only when the gap was non-zero, so
 * on those 13 boards it said nothing at all -- and silence is ambiguous. It
 * reads as "not calculated", which is the one thing it never is: `initiative`
 * is derived from two `protocolFloor` calls the panel already makes on every
 * render.
 *
 * `protocolFloor` is used here as an oracle for the precondition only. The test
 * asserts what the screen says, never what the engine should have returned, so
 * a wording change fails this file only if it changes the meaning.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { protocolFloor } from "../engine/protocol";
import { Verdict } from "./Verdict";

afterEach(cleanup);

const board = (fractions: number[][], over: Partial<Board> = {}): Board => ({
  id: "diceoff-ui",
  opponent: "Opponent 11",
  ourPlayers: ["Ana", "Bokur", "Sam", "Pete", "Rue"],
  theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
  fractions,
  scaleId: "five",
  ourTeamFirst: true,
  updatedAt: 0,
  ...over,
});

/** The gap the panel will compute, straight from the engine. */
function initiativeOf(b: Board): number {
  const matrix = boardMatrix(b, boardScale(b));
  return protocolFloor(matrix, true).value - protocolFloor(matrix, false).value;
}

/**
 * Every cell identical, so opening and receiving cannot differ. This is not a
 * contrived shape: the round-five board in the fixture set is 21 threes out of
 * 25 cells.
 *
 * Note the value. 0.5 is the sentinel `isRated` uses to mean "never touched"
 * (`some(|f - 0.5| > 1e-9)`), so a flat board of 0.5 is not a uniform board at
 * all -- it is an empty one, and Verdict short-circuits to "Not rated yet"
 * before any insight renders. Any uniform value other than 0.5 works.
 */
const FLAT: number[][] = Array.from({ length: 5 }, () => Array(5).fill(0.75));

/** Deliberately lopsided, to land on the other side of the branch. */
const LOPSIDED: number[][] = [
  [0.1, 0.9, 0.9, 0.9, 0.9],
  [0.9, 0.1, 0.2, 0.3, 0.4],
  [0.2, 0.8, 0.5, 0.5, 0.5],
  [0.3, 0.4, 0.5, 0.6, 0.7],
  [0.4, 0.5, 0.6, 0.7, 0.8],
];

describe("the dice-off insight", () => {
  it("says so out loud when the roll costs nothing", () => {
    const b = board(FLAT);
    expect(initiativeOf(b)).toBe(0);

    render(<Verdict board={b} dodgeMode="off" onHighlight={() => {}} />);

    expect(screen.getByText(/dice-off does not matter/i)).toBeTruthy();
    // The old behaviour was silence. Guard against it coming back.
    expect(screen.queryByText(/Going first costs/i)).toBeNull();
    expect(screen.queryByText(/Going first gains/i)).toBeNull();
  });

  it("still prices the roll when it is worth something", () => {
    const b = board(LOPSIDED);
    expect(initiativeOf(b)).not.toBe(0);

    render(<Verdict board={b} dodgeMode="off" onHighlight={() => {}} />);

    expect(screen.getByText(/Going first (costs|gains)/i)).toBeTruthy();
    expect(screen.queryByText(/dice-off does not matter/i)).toBeNull();
  });

  it("quotes both floors on a free board, so the claim can be checked", () => {
    const b = board(FLAT);
    const matrix = boardMatrix(b, boardScale(b));
    const floor = protocolFloor(matrix, true).value;

    render(<Verdict board={b} dodgeMode="off" onHighlight={() => {}} />);

    // Mirrors Verdict's own `fmt`: integers render bare, everything else to one
    // decimal. A uniform board lands on a whole number, so `toFixed(1)` would
    // look for "20.0" against a rendered "20" and fail for no real reason.
    const shown = Number.isInteger(floor) ? String(floor) : floor.toFixed(1);

    // The sentence must carry the number, not merely assert the two sides are
    // equal, otherwise there is nothing on screen to check against the
    // GUARANTEED stat sitting a few lines above it.
    const body = screen.getByText(/dice-off does not matter/i).closest("div");
    expect(body?.textContent).toContain(shown);
  });
});
