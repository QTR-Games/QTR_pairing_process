// @vitest-environment jsdom
/**
 * The opponent roster popup, at its edges.
 *
 * The grid's own value picker is exercised elsewhere; this file is only about
 * the roster affordance added to the column headers -- that it appears exactly
 * where an import left detail and nowhere else, that a hold (not a tap) opens
 * it, and that it renders the faction and lists it was given.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { emptyBoard, type Board } from "../model/board";
import { Grid } from "./Grid";

/**
 * A board whose first opponent carries full detail, whose second carries only a
 * name (the import found the player but no faction or lists), and whose third
 * carries a faction but no lists -- the three cases the header has to tell apart.
 */
function boardWithDetail(): Board {
  const board = emptyBoard();
  board.theirPlayers = ["Rook", "Nobody", "Halfknown", "Opponent 4", "Opponent 5"];
  board.theirDetails = [
    {
      name: "Rook",
      faction: "Corvid Compact",
      lists: [
        { leader: "Magpie Sorrel", army: "Rookery Vanguard" },
        { leader: "Crow", army: "Murder" },
      ],
    },
    { name: "Nobody" },
    { name: "Halfknown", faction: "Iron Host" },
  ];
  return board;
}

const holdName = (name: string) =>
  screen.queryByRole("button", { name: new RegExp(`^${name}\\. Hold for roster\\.$`) });

afterEach(cleanup);

describe("Grid opponent roster popup", () => {
  it("offers the affordance only for names an import gave detail", () => {
    render(<Grid board={boardWithDetail()} onChange={() => {}} />);
    // Full detail and faction-only both become hold targets; the bare name does not.
    expect(holdName("Rook")).not.toBeNull();
    expect(holdName("Halfknown")).not.toBeNull();
    expect(holdName("Nobody")).toBeNull();
  });

  it("opens the popup from the keyboard, showing faction and every list", () => {
    render(<Grid board={boardWithDetail()} onChange={() => {}} />);
    fireEvent.keyDown(holdName("Rook")!, { key: "Enter" });
    expect(screen.getByText("Corvid Compact")).toBeTruthy();
    expect(screen.getByText("Magpie Sorrel -- Rookery Vanguard")).toBeTruthy();
    expect(screen.getByText("Crow -- Murder")).toBeTruthy();
  });

  it("opens on a hold but not on a quick tap", () => {
    vi.useFakeTimers();
    try {
      render(<Grid board={boardWithDetail()} onChange={() => {}} />);
      const btn = holdName("Rook")!;

      // A tap: press then release before the hold elapses -> nothing opens.
      fireEvent.pointerDown(btn, { button: 0 });
      fireEvent.pointerUp(btn);
      act(() => {
        vi.advanceTimersByTime(600);
      });
      expect(screen.queryByText("Corvid Compact")).toBeNull();

      // A hold: press and wait -> the popup opens.
      fireEvent.pointerDown(btn, { button: 0 });
      act(() => {
        vi.advanceTimersByTime(600);
      });
      expect(screen.getByText("Corvid Compact")).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it("says so plainly when a rostered opponent has no lists", () => {
    render(<Grid board={boardWithDetail()} onChange={() => {}} />);
    fireEvent.keyDown(holdName("Halfknown")!, { key: "Enter" });
    expect(screen.getByText("Iron Host")).toBeTruthy();
    expect(screen.getByText(/No lists recorded/)).toBeTruthy();
  });

  it("leaves the header untouched on a hand-entered board", () => {
    // No theirDetails at all: every name is plain text, no hold targets.
    render(<Grid board={emptyBoard()} onChange={() => {}} />);
    expect(screen.queryByRole("button", { name: /Hold for roster/ })).toBeNull();
  });
});
