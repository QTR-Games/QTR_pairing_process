// @vitest-environment jsdom
/**
 * The advice-level toggle draws three different screens through one search.
 *
 * The engine does the same work at every level -- what changes is how much of
 * the "why" reaches the table. This suite pins the three states so a later edit
 * cannot quietly turn prose back on at `brief`, drop the recommendation at
 * `full`, or -- the one that would actually cost a game -- hide the raw rating
 * chips and pick values that a captain reads a decision off, at any level.
 *
 *   full   prose (tie-break reasoning, leverage) + hints (tags, recommendation)
 *   brief  hints only, no prose
 *   off    neither -- bare options, values and chips
 *
 * The structural data (option values, pick values, the grid-rating chips) is
 * the floor: it stays at all three levels, because turning advice down is not
 * the same as turning the numbers off.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import type { Board } from "../model/board";
import { newRound, type LiveState } from "../engine/live";
import type { AdviceLevel } from "../model/settings";
import { LivePanel } from "./LivePanel";

afterEach(cleanup);

const FRACTIONS: number[][] = [
  [0.5, 0.9, 0.4, 0.5, 0.6],
  [0.6, 0.5, 0.5, 0.1, 0.5],
  [0.4, 0.5, 0.5, 0.6, 0.8],
  [0.5, 0.6, 0.4, 0.5, 0.5],
  [0.2, 0.5, 0.6, 0.5, 0.5],
];

function board(ourTeamFirst: boolean): Board {
  return {
    id: "advice",
    opponent: "Opponent 02",
    ourPlayers: ["Pete", "Bokur", "Sam", "Ana", "Rue"],
    theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
    fractions: FRACTIONS,
    scaleId: "five",
    ourTeamFirst,
    updatedAt: 0,
  };
}

/** LivePanel is controlled, so the test owns the state the way App does. */
function Harness({ b, level }: { b: Board; level: AdviceLevel }) {
  const [state, setState] = useState<LiveState>(() =>
    newRound(b.ourPlayers.length, b.ourTeamFirst),
  );
  return (
    <LivePanel
      board={b}
      state={state}
      onState={setState}
      onReset={() => setState(newRound(b.ourPlayers.length, b.ourTeamFirst))}
      adviceLevel={level}
    />
  );
}

/** Tap the first row until the given selector appears, the way a phone does. */
function tapUntil(container: HTMLElement, selector: string, max = 20): void {
  let taps = 0;
  while (taps < max && container.querySelectorAll(selector).length === 0) {
    const row = container.querySelector("li.option");
    const btn =
      row?.querySelector<HTMLButtonElement>("button.pick") ??
      row?.querySelector<HTMLButtonElement>("button.tappable");
    if (!btn) break;
    fireEvent.click(btn);
    taps++;
  }
}

describe("advice-level toggle on the live round", () => {
  // Us-first opens on an "open" decision: every option row carries a hint tag,
  // and leverage renders as prose. That gives one screen where both gated
  // layers and the structural floor are all visible at once.
  it("full shows prose and hints", () => {
    const { container } = render(<Harness b={board(true)} level="full" />);
    expect(container.querySelector(".leverage")).not.toBeNull(); // prose
    expect(container.querySelector(".option-meta .tag")).not.toBeNull(); // hint
    expect(container.querySelector(".option-value")).not.toBeNull(); // structural
  });

  it("brief drops prose but keeps hints", () => {
    const { container } = render(<Harness b={board(true)} level="brief" />);
    expect(container.querySelector(".leverage")).toBeNull(); // no prose
    expect(container.querySelector(".tiebreak")).toBeNull(); // no prose
    expect(container.querySelector(".option-meta .tag")).not.toBeNull(); // hint kept
    expect(container.querySelector(".option-value")).not.toBeNull(); // structural
  });

  it("off drops prose and hints but keeps the bare options", () => {
    const { container } = render(<Harness b={board(true)} level="off" />);
    expect(container.querySelector(".leverage")).toBeNull(); // no prose
    expect(container.querySelector(".tiebreak")).toBeNull(); // no prose
    expect(container.querySelector(".option-meta .tag")).toBeNull(); // no hint
    expect(container.querySelector(".pick-hint")).toBeNull(); // no hint
    expect(container.querySelector(".option-value")).not.toBeNull(); // structural
  });

  // The chips and pick values are F2's whole point: the captain's own grid
  // numbers, surfaced so he can override the projection. Turning advice off
  // must not take them with it.
  it("keeps the grid-rating chips and pick values even at off", () => {
    const { container } = render(<Harness b={board(false)} level="off" />);
    tapUntil(container, ".pick-rating");

    expect(container.querySelectorAll(".pick-rating").length).toBeGreaterThan(0);
    expect(container.querySelectorAll(".pick-value").length).toBeGreaterThan(0);
    // ...but the advice layered on those tiles is gone.
    expect(container.querySelector(".pick-hint")).toBeNull();
    expect(container.querySelector(".pick-best")).toBeNull();
  });

  // The recommendation the captain acts on at brief: a one-line "Take X" when
  // the numbers separate, with none of the paragraph behind it.
  it("brief keeps the one-line pick recommendation without the paragraph", () => {
    const { container } = render(<Harness b={board(false)} level="brief" />);
    tapUntil(container, ".pick-hint");

    const hint = container.querySelector(".pick-hint");
    expect(hint).not.toBeNull();
    // The verbose variants all open with "Both hold" -- brief must never reach
    // them, however the floor ties.
    expect(hint?.textContent ?? "").not.toContain("Both hold");
  });
});
