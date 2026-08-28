// @vitest-environment jsdom
/**
 * The per-card currency toggle, on the screen rather than in the model.
 *
 * Each Verdict insight can be read in either rating points or round-win chance,
 * and the captain chooses per card. The choice is made with a long-press on
 * mobile or a right-click on desktop, but the load-bearing control -- the one
 * the keyboard and this test both reach -- is the small unit pill in the card's
 * corner. It is a real button with an aria-label, so exercising it here is the
 * same path a keyboard user takes.
 *
 * Two things have to hold and both are asserted against rendered text and real
 * storage, never against the model:
 *
 *   * clicking the pill swaps THAT card's wording and leaves the rest alone;
 *   * the choice survives a remount, because it is written to settings.
 *
 * The dice-off card is the subject because it is the one insight that always
 * renders regardless of board shape, so the test never depends on a gate.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Board } from "../model/board";
import { loadSettings } from "../model/settings";
import { Verdict } from "./Verdict";

afterEach(cleanup);
afterEach(() => localStorage.clear());

/** Lopsided on purpose, so the points dice-off shows a "Going first" verb. */
const LOPSIDED: number[][] = [
  [0.1, 0.9, 0.9, 0.9, 0.9],
  [0.9, 0.1, 0.2, 0.3, 0.4],
  [0.2, 0.8, 0.5, 0.5, 0.5],
  [0.3, 0.4, 0.5, 0.6, 0.7],
  [0.4, 0.5, 0.6, 0.7, 0.8],
];

const board = (): Board => ({
  id: "cardtoggle-ui",
  opponent: "Opponent 12",
  ourPlayers: ["Ana", "Bokur", "Sam", "Pete", "Rue"],
  theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
  fractions: LOPSIDED,
  scaleId: "five",
  ourTeamFirst: true,
  updatedAt: 0,
});

/** The dice-off card in whichever wording it currently wears. */
function diceOffCard(): HTMLElement {
  const title = screen.getByText(/Going first (costs|gains)|dice-off, in round-win chance/i);
  return title.closest(".insight") as HTMLElement;
}

describe("the per-card currency pill", () => {
  it("flips a single card's wording when clicked, defaulting the dice-off to points", () => {
    render(<Verdict board={board()} dodgeMode="off" onHighlight={() => {}} />);

    // Dice-off ships in points: it names the initiative gap with a verb.
    expect(screen.getByText(/Going first (costs|gains)/i)).toBeTruthy();
    expect(screen.queryByText(/dice-off, in round-win chance/i)).toBeNull();

    fireEvent.click(within(diceOffCard()).getByRole("button"));

    // Now in chance: the verb is gone and the option-B heading is present.
    expect(screen.getByText(/dice-off, in round-win chance/i)).toBeTruthy();
    expect(screen.queryByText(/Going first (costs|gains)/i)).toBeNull();
  });

  it("persists the choice to settings so a remount keeps it", () => {
    const { unmount } = render(<Verdict board={board()} dodgeMode="off" onHighlight={() => {}} />);
    fireEvent.click(within(diceOffCard()).getByRole("button"));

    expect(loadSettings().cardUnits.diceOff).toBe("chance");

    unmount();
    render(<Verdict board={board()} dodgeMode="off" onHighlight={() => {}} />);
    // The remounted panel reads the stored choice, not the default.
    expect(screen.getByText(/dice-off, in round-win chance/i)).toBeTruthy();
  });

  it("does not disturb the other cards when one is toggled", () => {
    render(<Verdict board={board()} dodgeMode="off" onHighlight={() => {}} />);

    // Protocol-protects defaults to chance, so it names round-win chance up
    // front. Toggling the dice-off must not touch it.
    const protectBefore = screen.queryByText(/protocol protects .*round-win chance/i);
    fireEvent.click(within(diceOffCard()).getByRole("button"));
    const protectAfter = screen.queryByText(/protocol protects .*round-win chance/i);

    expect(Boolean(protectBefore)).toBe(Boolean(protectAfter));
    expect(loadSettings().cardUnits.protocolProtects ?? "chance").toBe("chance");
  });
});
