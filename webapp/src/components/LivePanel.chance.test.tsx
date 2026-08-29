// @vitest-environment jsdom
/**
 * The live round speaks the same currency as the rest of the app.
 *
 * Issue #120: the pairing-off tree still read in raw points while every other
 * screen had moved to round-win chance. The projected-score numbers on each
 * card -- the offer total and the two pick totals -- plus the header threshold
 * are the three places a captain reads a decision off, so they must all print
 * as a percentage. The one number that must NOT change is the matchup-rating
 * chip: that is the captain's own grid entry, surfaced so he can override the
 * projection, and it stays a raw rating.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { newRound, type LiveState } from "../engine/live";
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
    id: "chance",
    opponent: "Opponent 02",
    ourPlayers: ["Pete", "Bokur", "Sam", "Ana", "Rue"],
    theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
    fractions: FRACTIONS,
    scaleId: "five",
    ourTeamFirst,
    updatedAt: 0,
  };
}

function Harness({ b }: { b: Board }) {
  const [state, setState] = useState<LiveState>(() =>
    newRound(b.ourPlayers.length, b.ourTeamFirst),
  );
  return (
    <LivePanel
      board={b}
      state={state}
      onState={setState}
      onReset={() => setState(newRound(b.ourPlayers.length, b.ourTeamFirst))}
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

const isPercent = (text: string): boolean => /%$/.test(text.trim());

describe("live round reads in round-win chance", () => {
  it("prints the header threshold as a percentage", () => {
    render(<Harness b={board(true)} />);
    expect(screen.getByText(/to take the round/).textContent ?? "").toMatch(/\d+%|under 1%/);
  });

  it("prints every option total as a percentage, not raw points", () => {
    const { container } = render(<Harness b={board(true)} />);
    const values = container.querySelectorAll<HTMLElement>(".option-value");
    expect(values.length).toBeGreaterThan(0);
    for (const v of values) {
      expect(isPercent(v.textContent ?? ""), `"${v.textContent}" should be a percentage`).toBe(true);
    }
  });

  it("prints every pick total as a percentage while keeping the raw rating chip", () => {
    const b = board(false); // them-first opens straight onto an offer with pick tiles
    const { container } = render(<Harness b={b} />);
    tapUntil(container, ".pick-value");

    const picks = container.querySelectorAll<HTMLElement>(".pick-value");
    expect(picks.length).toBeGreaterThan(0);
    for (const p of picks) {
      expect(isPercent(p.textContent ?? ""), `"${p.textContent}" should be a percentage`).toBe(true);
    }

    // The chip stays the captain's own grid rating -- a bare number from the
    // board, never a percentage.
    const matrix = boardMatrix(b, boardScale(b));
    const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
    const gridValues = new Set(matrix.flat().map(fmt));
    const chips = container.querySelectorAll<HTMLElement>(".pick-rating");
    expect(chips.length).toBeGreaterThan(0);
    for (const chip of chips) {
      const text = chip.textContent ?? "";
      expect(isPercent(text)).toBe(false);
      expect(gridValues.has(text)).toBe(true);
    }
  });
});
