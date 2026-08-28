// @vitest-environment jsdom
/**
 * The grid cell readout, and the opponent roster popup, at their edges.
 *
 * The first suite guards issue #93: the grid used to render each cell as a
 * SPREAD-compressed win percentage, so on the 1-10 scale picking a 1 showed 8
 * and a 10 showed 93 -- "a much different value than I selected". A cell now
 * reads back the rating that was chosen, on the board's own scale, matching the
 * value picker.
 *
 * The rest is the roster affordance added to the column headers -- that it
 * appears exactly where an import left detail and nowhere else, that a hold (not
 * a tap) opens it, and that it renders the faction and lists it was given.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { boardScale, emptyBoard, setRating, type Board } from "../model/board";
import { Grid } from "./Grid";

afterEach(cleanup);

describe("Grid cell readout", () => {
  it("echoes the chosen rating on the 1-10 scale, not a win percentage", () => {
    // The exact #93 report: ratings 1..5 down the first row used to read back
    // as 8, 17, 26, 36, 45. They must read back as themselves.
    let board = emptyBoard("ten");
    const scale = boardScale(board);
    for (let j = 0; j < 5; j++) {
      board = setRating(board, 0, j, j + 1, scale);
    }
    render(<Grid board={board} onChange={() => {}} />);

    const readouts = ["1", "2", "3", "4", "5"].map(
      (_, j) =>
        screen.getByRole("button", { name: `Player 1 versus Opponent ${j + 1}` }).textContent,
    );
    expect(readouts).toEqual(["1", "2", "3", "4", "5"]);
  });

  it.each([
    ["five", 0.75, "4"],
    ["fiveHalf", 0.625, "3.5"],
  ])("displays the picked scale value on the %s scale", (scaleId, fraction, expected) => {
    const board = emptyBoard(scaleId);
    board.fractions[0][0] = fraction;

    render(<Grid board={board} onChange={() => {}} />);

    expect(
      screen.getByRole("button", { name: "Player 1 versus Opponent 1" }).textContent,
    ).toBe(expected);
  });

  it("shows the picked value back after selecting it", () => {
    let board = emptyBoard("ten");
    const onChange = vi.fn((b: Board) => {
      board = b;
    });
    const { rerender } = render(<Grid board={board} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Player 1 versus Opponent 1" }));
    fireEvent.click(screen.getByRole("button", { name: "9" }));

    rerender(<Grid board={board} onChange={onChange} />);
    expect(
      screen.getByRole("button", { name: "Player 1 versus Opponent 1" }).textContent,
    ).toBe("9");
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

describe("Grid cell info popup", () => {
  const cells = () => screen.getAllByRole("button", { name: /versus/ });

  it("opens the cell info popup on a hold and swallows the tap that follows", () => {
    vi.useFakeTimers();
    try {
      render(
        <Grid
          board={emptyBoard()}
          onChange={() => {}}
          cellInfo={(ours, theirs) => (
            <p>
              held {ours}-{theirs}
            </p>
          )}
        />,
      );
      const cell = cells()[0];

      // A hold: press and wait -> the info popup opens.
      fireEvent.pointerDown(cell, { button: 0 });
      act(() => {
        vi.advanceTimersByTime(600);
      });
      expect(screen.getByText("held 0-0")).toBeTruthy();

      // The click the browser fires after the release must NOT also open the
      // value editor on top of it.
      fireEvent.click(cell);
      expect(screen.queryByText(/Worst matchup on the left/)).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("opens the value editor on a quick tap even when cell info is available", () => {
    vi.useFakeTimers();
    try {
      render(<Grid board={emptyBoard()} onChange={() => {}} cellInfo={() => <p>held</p>} />);
      const cell = cells()[0];

      // A tap: press then release before the hold elapses, then the click.
      fireEvent.pointerDown(cell, { button: 0 });
      fireEvent.pointerUp(cell);
      act(() => {
        vi.advanceTimersByTime(600);
      });
      fireEvent.click(cell);

      expect(screen.getByText(/Worst matchup on the left/)).toBeTruthy();
      expect(screen.queryByText("held")).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("has no hold gesture when no cell info is supplied", () => {
    render(<Grid board={emptyBoard()} onChange={() => {}} />);
    fireEvent.click(cells()[0]);
    // Tapping still opens the value editor, exactly as before this prop existed.
    expect(screen.getByText(/Worst matchup on the left/)).toBeTruthy();
  });
});
