// @vitest-environment jsdom
/**
 * The live round speaks the same currency as the rest of the app.
 *
 * Issue #120: the pairing-off tree still read in raw points while every other
 * screen had moved to round-win chance. The projected-score numbers on each
 * card -- the offer total and the two pick totals -- plus the header threshold
 * are the three places a captain reads a decision off, so they must all print
 * as a percentage.
 *
 * Issue #126: #120 and #121 left the numbers between those headlines behind,
 * so a card could read 62% beside a hold-or-play line reading 5. Everything the
 * round prints now follows one unit. Issue #127 makes that unit a setting, and
 * the load-bearing promise of a display setting is that it changes only how a
 * figure is spelled -- never which option the panel recommends.
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

function Harness({ b, unit }: { b: Board; unit?: "points" | "chance" }) {
  const [state, setState] = useState<LiveState>(() =>
    newRound(b.ourPlayers.length, b.ourTeamFirst),
  );
  return (
    <LivePanel
      board={b}
      state={state}
      onState={setState}
      onReset={() => setState(newRound(b.ourPlayers.length, b.ourTeamFirst))}
      roundUnit={unit}
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

  it("prints every pick total and rating chip as a percentage, raw rating on the tooltip", () => {
    const b = board(false); // them-first opens straight onto an offer with pick tiles
    const { container } = render(<Harness b={b} />);
    tapUntil(container, ".pick-value");

    const picks = container.querySelectorAll<HTMLElement>(".pick-value");
    expect(picks.length).toBeGreaterThan(0);
    for (const p of picks) {
      expect(isPercent(p.textContent ?? ""), `"${p.textContent}" should be a percentage`).toBe(true);
    }

    // A single matchup rating is the one quantity that converts exactly to a
    // win probability, so in chance mode the chip reads as one -- but the
    // captain's own grid number stays reachable on the tooltip, because it is
    // the only figure he can check against the sheet he wrote.
    const matrix = boardMatrix(b, boardScale(b));
    const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
    const gridValues = new Set(matrix.flat().map(fmt));
    const chips = container.querySelectorAll<HTMLElement>(".pick-rating");
    expect(chips.length).toBeGreaterThan(0);
    for (const chip of chips) {
      expect(isPercent(chip.textContent ?? "")).toBe(true);
      const tip = chip.getAttribute("title") ?? "";
      expect(gridValues.has(tip.split(": ").pop() ?? "")).toBe(true);
    }
  });

  /**
   * Issue #126 in one assertion: every figure-bearing element on the screen,
   * not just the three headline ones #120 fixed. Listing the selectors rather
   * than scanning all text is deliberate -- prose carries counts ("3 of their
   * 5 replies") that are not round values and must stay bare. It walks the
   * round because cost tags and the hold-or-play list do not appear on the
   * opening screen, and a check that never reaches an element proves nothing.
   */
  it("leaves no figure on the screen in the other currency", () => {
    const selectors = [
      ".option-value",
      ".tag.cost",
      ".leverage-lead",
      ".leverage .gain",
      ".profile-upside",
      ".profile-risk",
    ];
    const seen = new Map(selectors.map((s) => [s, 0]));

    for (const first of [true, false]) {
      const { container } = render(<Harness b={board(first)} />);
      for (let tap = 0; tap < 12; tap++) {
        for (const sel of selectors) {
          for (const el of container.querySelectorAll<HTMLElement>(sel)) {
            const text = (el.textContent ?? "")
              // "3 of 5 replies" counts replies, not round value. Strip the
              // phrase rather than exempting the element, so the figure that
              // follows it is still checked.
              .replace(/\d+ of \d+ replies|\d+ give you more/g, "");
            if (!/\d/.test(text)) continue; // "same floor", "Nothing in it"
            seen.set(sel, (seen.get(sel) ?? 0) + 1);
            for (const token of text.match(/\d+(?:\.\d+)?%?/g) ?? []) {
              expect(token, `${sel} printed a bare number in "${text}"`).toMatch(/%$/);
            }
          }
        }
        const row = container.querySelector("li.option");
        const btn =
          row?.querySelector<HTMLButtonElement>("button.pick") ??
          row?.querySelector<HTMLButtonElement>("button.tappable");
        if (!btn) break;
        fireEvent.click(btn);
      }
      cleanup();
    }

    // Every selector must have been reached, or the walk missed the screen the
    // bug lived on and the assertion above was never exercised there.
    for (const sel of selectors) {
      expect(seen.get(sel), `never reached ${sel}`).toBeGreaterThan(0);
    }
  });
});

describe("the round unit is a display setting", () => {
  it("prints raw points, not percentages, when asked for points", () => {
    const { container } = render(<Harness b={board(true)} unit="points" />);
    const values = container.querySelectorAll<HTMLElement>(".option-value");
    expect(values.length).toBeGreaterThan(0);
    for (const v of values) {
      expect(isPercent(v.textContent ?? ""), `"${v.textContent}" should be points`).toBe(false);
      expect(Number.isFinite(Number(v.textContent))).toBe(true);
    }
  });

  /**
   * The load-bearing promise. A captain who flips this mid-event must get the
   * same advice back in different words -- if the toggle could reorder the
   * options or move the recommendation, it would be a strategy setting wearing
   * a formatter's clothes.
   */
  it("does not change the order of the options or which one is recommended", () => {
    const labels = (c: HTMLElement) =>
      [...c.querySelectorAll<HTMLElement>(".option-label")].map((e) => e.textContent);
    const best = (c: HTMLElement) =>
      [...c.querySelectorAll<HTMLElement>(".tag")]
        .filter((e) => /best|strongest/.test(e.textContent ?? ""))
        .map((e) => e.closest("li.option")?.querySelector(".option-label")?.textContent);

    const chance = render(<Harness b={board(true)} unit="chance" />).container;
    const order = labels(chance);
    const pick = best(chance);
    cleanup();

    const points = render(<Harness b={board(true)} unit="points" />).container;
    expect(labels(points)).toEqual(order);
    expect(best(points)).toEqual(pick);
    expect(order.length).toBeGreaterThan(1);
    expect(pick.length).toBeGreaterThan(0);
  });
});
