// @vitest-environment jsdom
/*
  Plan A of #83: record which equally-exposed player the captain protects first,
  mark it on the grid, persist it -- and say plainly it does NOT yet steer the
  engine. These pin the three things that make it a recorded decision rather than
  the "free-text note" that was rejected:

    * the control only appears at the genuine "I have to choose" moment (two or
      more players tied at the top of the exposed order) and only when a writer
      is wired, so it can never be a dead UI;
    * choosing writes the index back through onBoardChange (which the app already
      autosaves), and "No preference" clears it;
    * the copy claims exactly what it does and refuses the claim it doesn't.

  The tie boards are synthetic doubled-1 rows on 4s filler. That matters: no real
  fixture in the repo has a player with two 1s -- the owner's own stated worry
  case -- so forcedLevel never reaches 1 anywhere in the suite. These boards are
  the only place the floor-of-the-scale tie is exercised end to end.
*/

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Board } from "../model/board";
import { Grid } from "./Grid";
import { Verdict } from "./Verdict";

afterEach(cleanup);

function boardFromRatings(rows: number[][], protectPriority?: number | null): Board {
  return {
    id: "protect-test",
    opponent: "Test",
    ourPlayers: ["Ana", "Bok", "Sam", "Pete", "Rue"],
    theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
    // Fractions are scale-free; 1-5 ratings map straight in on the five scale.
    fractions: rows.map((r) => r.map((v) => (v - 1) / 4)),
    scaleId: "five",
    ourTeamFirst: true,
    updatedAt: 0,
    ...(protectPriority === undefined ? {} : { protectPriority }),
  };
}

// Two players each forced onto a doubled 1 -- tied at the bottom of the scale,
// the case the fixtures never contain. Rows 2-4 are safe 4s filler (all-3s
// filler manufactures its own traps, so 4s keeps the only bad cells the ones
// under test).
const DOUBLED_ONE_TIE = [
  [4, 1, 4, 1, 4],
  [4, 1, 4, 1, 4],
  [4, 4, 4, 4, 4],
  [4, 4, 4, 4, 4],
  [4, 4, 4, 4, 4],
];

// Only one player exposed: no "I have to choose", so no control.
const SINGLE_EXPOSED = [
  [4, 1, 4, 1, 4],
  [4, 4, 4, 4, 4],
  [4, 4, 4, 4, 4],
  [4, 4, 4, 4, 4],
  [4, 4, 4, 4, 4],
];

function protectGroup(): HTMLElement {
  return screen.getByRole("radiogroup", { name: "Protect first" });
}

describe("protect-first control (Verdict)", () => {
  it("appears only when players are tied AND a writer is wired", () => {
    // No writer: nothing to record into, so the control must not show.
    render(<Verdict board={boardFromRatings(DOUBLED_ONE_TIE)} dodgeMode="off" />);
    expect(screen.queryByRole("radiogroup", { name: "Protect first" })).toBeNull();

    cleanup();
    // Writer wired and a real tie: the control shows the two tied players plus a
    // default of no preference.
    render(
      <Verdict
        board={boardFromRatings(DOUBLED_ONE_TIE)}
        dodgeMode="off"
        onBoardChange={vi.fn()}
      />,
    );
    const group = protectGroup();
    expect(within(group).getByRole("radio", { name: "No preference" })).toBeTruthy();
    expect(within(group).getByRole("radio", { name: "Ana" })).toBeTruthy();
    expect(within(group).getByRole("radio", { name: "Bok" })).toBeTruthy();
    // Nobody chosen yet -> "No preference" is the checked default.
    expect(
      (within(group).getByRole("radio", { name: "No preference" }) as HTMLInputElement).checked,
    ).toBe(true);
  });

  it("stays hidden when only one player is exposed", () => {
    render(
      <Verdict
        board={boardFromRatings(SINGLE_EXPOSED)}
        dodgeMode="off"
        onBoardChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("radiogroup", { name: "Protect first" })).toBeNull();
  });

  it("records the captain's pick through onBoardChange", () => {
    const onBoardChange = vi.fn();
    render(
      <Verdict board={boardFromRatings(DOUBLED_ONE_TIE)} dodgeMode="off" onBoardChange={onBoardChange} />,
    );
    fireEvent.click(within(protectGroup()).getByRole("radio", { name: "Bok" }));
    expect(onBoardChange).toHaveBeenCalledTimes(1);
    // Bok is our player index 1.
    expect(onBoardChange).toHaveBeenCalledWith(expect.objectContaining({ protectPriority: 1 }));
  });

  it("clears the pick when No preference is chosen", () => {
    const onBoardChange = vi.fn();
    // Start with Ana (index 0) already chosen; she is exposed, so it is live.
    render(
      <Verdict
        board={boardFromRatings(DOUBLED_ONE_TIE, 0)}
        dodgeMode="off"
        onBoardChange={onBoardChange}
      />,
    );
    const group = protectGroup();
    expect((within(group).getByRole("radio", { name: "Ana" }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(within(group).getByRole("radio", { name: "No preference" }));
    expect(onBoardChange).toHaveBeenCalledWith(expect.objectContaining({ protectPriority: null }));
  });

  it("says what the choice does and refuses the claim it doesn't", () => {
    render(
      <Verdict board={boardFromRatings(DOUBLED_ONE_TIE)} dodgeMode="off" onBoardChange={vi.fn()} />,
    );
    const note = within(protectGroup().parentElement!).getByText(
      /note to yourself/i,
    );
    // The load-bearing disclaimer: it is marked and saved, and it does NOT steer
    // the suggestions yet. Without this the control would be a UI that lies.
    expect(note.textContent).toMatch(/marked on the grid/i);
    expect(note.textContent).toMatch(/does not change the pairing suggestions yet/i);
  });
});

describe("protect-first marker (Grid)", () => {
  const container = () =>
    render(
      <Grid board={boardFromRatings(DOUBLED_ONE_TIE, 0)} onChange={vi.fn()} />,
    ).container;

  it("marks the chosen row and only that row", () => {
    const c = container();
    const marks = c.querySelectorAll(".protect-mark");
    expect(marks.length).toBe(1);
    // It sits in Ana's row header, not anyone else's.
    const rowHead = marks[0].closest("th.row-head");
    expect(rowHead?.textContent).toContain("Ana");
  });

  it("marks nothing for an out-of-range stored index", () => {
    const c = render(
      <Grid board={boardFromRatings(DOUBLED_ONE_TIE, 9)} onChange={vi.fn()} />,
    ).container;
    expect(c.querySelectorAll(".protect-mark").length).toBe(0);
  });

  it("marks nothing when there is no preference", () => {
    const c = render(
      <Grid board={boardFromRatings(DOUBLED_ONE_TIE)} onChange={vi.fn()} />,
    ).container;
    expect(c.querySelectorAll(".protect-mark").length).toBe(0);
  });
});
