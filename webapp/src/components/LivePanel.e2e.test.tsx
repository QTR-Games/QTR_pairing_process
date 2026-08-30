// @vitest-environment jsdom
/**
 * Drive a whole round by tapping, the way a phone does.
 *
 * Everything else in this suite calls the engine directly. That proves the
 * search is right and proves nothing at all about the screen in front of you at
 * the table: a row wired to the wrong index, an offer that commits the attacker
 * as the defender, a "done" state the panel cannot render. All of it passes 69
 * engine tests and fails on the first round of the event.
 *
 * So this test never imports the engine to decide what to do. It looks at the
 * DOM, taps the first control it finds, and repeats until the round says it is
 * over -- then checks the result against the engine as an oracle. If the wiring
 * disagrees with the search, the two disagree here.
 *
 * Only the environment is jsdom, set per-file above, so the node-based tests
 * that stub their own storage are untouched.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { currentDecision, newRound, type LiveState } from "../engine/live";
import { LivePanel } from "./LivePanel";

/*
 * `screen` queries document.body, and testing-library only auto-unmounts when
 * vitest runs with `globals: true`. This project does not, so without this each
 * test would query the leftover DOM of every test before it -- which shows up
 * as "found multiple elements" on the Restart button.
 */
afterEach(cleanup);

/**
 * A board with real texture: mostly near the middle, a few genuine outliers.
 *
 * A flat board would let a broken row ordering pass unnoticed, because every
 * option would be worth the same. The spread here is what makes a mis-wired tap
 * change the banked total.
 */
const FRACTIONS: number[][] = [
  [0.5, 0.9, 0.4, 0.5, 0.6],
  [0.6, 0.5, 0.5, 0.1, 0.5],
  [0.4, 0.5, 0.5, 0.6, 0.8],
  [0.5, 0.6, 0.4, 0.5, 0.5],
  [0.2, 0.5, 0.6, 0.5, 0.5],
];

function board(ourTeamFirst: boolean): Board {
  return {
    id: "e2e",
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
function Harness({ b, onState }: { b: Board; onState: (s: LiveState) => void }) {
  const [state, setState] = useState<LiveState>(() =>
    newRound(b.ourPlayers.length, b.ourTeamFirst),
  );
  return (
    <LivePanel
      board={b}
      state={state}
      onState={(s) => {
        onState(s);
        setState(s);
      }}
      onReset={() => setState(newRound(b.ourPlayers.length, b.ourTeamFirst))}
    />
  );
}

/**
 * Tap whatever the screen currently offers.
 *
 * An offer renders its two halves as `.pick` buttons and has no tappable
 * headline, so the pick buttons have to be tried first; an open or forced
 * decision renders one `.option-main.tappable` button per row. Taking the
 * first row in either case means this walks the line the app recommends, which
 * is the line a user following the app would actually play.
 */
function tapSomething(container: HTMLElement): boolean {
  const firstRow = container.querySelector("li.option");
  if (!firstRow) return false;

  const pick = firstRow.querySelector<HTMLButtonElement>("button.pick");
  if (pick) {
    fireEvent.click(pick);
    return true;
  }

  const tappable = firstRow.querySelector<HTMLButtonElement>("button.tappable");
  if (tappable) {
    fireEvent.click(tappable);
    return true;
  }

  return false;
}

describe("playing a round by tapping", () => {
  for (const ourTeamFirst of [true, false]) {
    it(`reaches a complete round with ${ourTeamFirst ? "us" : "them"} opening`, () => {
      const b = board(ourTeamFirst);
      let latest: LiveState | null = null;
      const { container } = render(<Harness b={b} onState={(s) => (latest = s)} />);

      // Five tables, each needing at most two taps, plus slack. A round that
      // cannot finish inside this has a loop in it, and the guard reports that
      // as a failure rather than hanging the suite.
      let taps = 0;
      while (taps < 40) {
        if (screen.queryByText(/Round complete/i)) break;
        if (!tapSomething(container)) break;
        taps++;
      }

      expect(screen.queryByText(/Round complete/i)).not.toBeNull();

      const state = latest as unknown as LiveState;
      expect(state).not.toBeNull();
      expect(currentDecision(state).kind).toBe("done");

      // Every player used exactly once, on both sides. A mis-wired tap that
      // commits the wrong index shows up here first.
      expect(state.committed).toHaveLength(5);
      expect(new Set(state.committed.map((c) => c.ours)).size).toBe(5);
      expect(new Set(state.committed.map((c) => c.theirs)).size).toBe(5);
      expect(state.ourPool).toBe(0);
      expect(state.theirPool).toBe(0);

      // The screen's own summary has to agree with the state behind it.
      const setList = container.querySelector(".committed ul");
      expect(setList).not.toBeNull();
      expect(within(setList as HTMLElement).getAllByRole("listitem")).toHaveLength(5);

      // The engine is the oracle: banked is the sum of the rated matchups the
      // taps actually committed, not whatever the panel chose to display.
      const matrix = boardMatrix(b, boardScale(b));
      const expected = state.committed.reduce((sum, c) => sum + matrix[c.ours][c.theirs], 0);
      expect(state.banked).toBeCloseTo(expected, 9);
      for (const c of state.committed) {
        expect(c.value).toBeCloseTo(matrix[c.ours][c.theirs], 9);
      }
    });
  }

  it("shows the running count and round-win chance as tables are set", () => {
    const b = board(true);
    const { container } = render(<Harness b={b} onState={() => {}} />);

    expect(screen.getByText(/0 of 5 tables set/)).toBeTruthy();

    // Tap until a table is actually set rather than a fixed number of times:
    // an open costs a tap and pairs nobody, so how many taps that takes is a
    // property of the protocol, not something this test should assert.
    let taps = 0;
    while (taps < 10 && !container.querySelector(".committed")) {
      if (!tapSomething(container)) break;
      taps++;
    }

    expect(container.querySelector(".committed")).not.toBeNull();
    expect(screen.queryByText(/0 of 5 tables set/)).toBeNull();
    expect(screen.getByText(/to take the round/)).toBeTruthy();
  });

  it("restarts back to an empty round", () => {
    const b = board(true);
    const { container } = render(<Harness b={b} onState={() => {}} />);

    let taps = 0;
    while (taps < 10 && !container.querySelector(".committed")) {
      if (!tapSomething(container)) break;
      taps++;
    }
    expect(container.querySelector(".committed")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /restart/i }));

    expect(screen.getByText(/0 of 5 tables set/)).toBeTruthy();
    expect(container.querySelector(".committed")).toBeNull();
  });

  it("keeps each pairing chip anchored to a real cell of our grid", () => {
    // Them-first, so the very first decision is an offer whose two halves are
    // fixed pairings -- exactly the tiles the captain reads a rating off. The
    // chip's face follows the round unit, but its tooltip must always carry a
    // real cell of our grid formatted the way the panel formats points, or the
    // chip is decorative at best and wrong at worst.
    const b = board(false);
    const { container } = render(<Harness b={b} onState={() => {}} />);

    const matrix = boardMatrix(b, boardScale(b));
    const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
    const gridValues = new Set(matrix.flat().map(fmt));

    // Walk until a screen that carries rating chips appears (an offer's pick
    // tiles or a forced pairing), the same way a user taps into the round.
    let taps = 0;
    let chips = container.querySelectorAll<HTMLElement>(".pick-rating");
    while (taps < 20 && chips.length === 0) {
      if (!tapSomething(container)) break;
      taps++;
      chips = container.querySelectorAll<HTMLElement>(".pick-rating");
    }

    expect(chips.length).toBeGreaterThan(0);
    for (const chip of chips) {
      // The tooltip ends in the raw rating. Membership in the grid catches a
      // wrong source or a wrong scale, which is what the chip could get wrong.
      const tip = chip.getAttribute("title") ?? "";
      const raw = tip.split(": ").pop() ?? "";
      expect(gridValues.has(raw), `"${tip}" should end in one of our ratings`).toBe(true);
    }
  });
});
