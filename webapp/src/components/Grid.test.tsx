// @vitest-environment jsdom
/**
 * The matchup sheet, checked where issue #93 said it lied.
 *
 * The grid used to render each cell as a SPREAD-compressed win percentage,
 * so picking a 1 on the English 1-10 scale showed 8 and picking a 10 showed
 * 93 -- "a much different value than I selected". A cell now reads back the
 * rating that was chosen, on the board's own scale, matching the value picker.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { emptyBoard, setRating, type Board } from "../model/board";
import { boardScale } from "../model/board";
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
