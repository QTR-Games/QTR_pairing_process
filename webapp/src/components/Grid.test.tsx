// @vitest-environment jsdom
/**
 * The matchup sheet, at two edges that have each misbehaved.
 *
 * The first suite guards issue #93: the grid used to render each cell as a
 * SPREAD-compressed win percentage, so picking a 1 on the English 1-10 scale
 * showed 8 and a 10 showed 93 -- "a much different value than I selected". A
 * cell now reads back the rating that was chosen, on the board's own scale,
 * matching the value picker.
 *
 * The second suite covers the opponent roster popup on the column headers --
 * that it appears exactly where an import left detail and nowhere else, that a
 * hold (not a tap) opens it, and that it renders the faction and lists it was
 * given.
 */
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { boardScale, emptyBoard, setRating, type Board } from "../model/board";
import { Grid } from "./Grid";

afterEach(cleanup);

/** A 1-10 board with one row of ratings 1..5 set on the first player. */
function tenBoard(): Board {
  let board = emptyBoard("ten");
  const scale = boardScale(board);
  for (let j = 0; j < 5; j++) {
    board = setRating(board, 0, j, j + 1, scale);
  }
  return board;
}

/** The five cell buttons on a player's row, in opponent order. */
function rowCells(rowLabel: string): HTMLButtonElement[] {
  const row = screen.getByRole("row", { name: new RegExp(rowLabel) });
  return within(row)
    .getAllByRole("button")
    .filter((b) => b.className.split(" ").includes("cell")) as HTMLButtonElement[];
}

describe("Grid cell readout", () => {
  it("echoes the chosen rating, not a win percentage", () => {
    render(<Grid board={tenBoard()} onChange={vi.fn()} />);
    const cells = rowCells("Player 1");
    expect(cells.map((c) => c.textContent)).toEqual(["1", "2", "3", "4", "5"]);
  });

  it("labels the readout column as ratings", () => {
    render(<Grid board={emptyBoard("ten")} onChange={vi.fn()} />);
    expect(screen.getByText("rating")).toBeTruthy();
  });

  it("shows the picked value back after selecting it", () => {
    let board = emptyBoard("ten");
    const onChange = vi.fn((b: Board) => {
      board = b;
    });
    const { rerender } = render(<Grid board={board} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: /Player 1 versus Opponent 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "9" }));

    rerender(<Grid board={board} onChange={onChange} />);
    expect(rowCells("Player 1")[0].textContent).toBe("9");
  });
});

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
