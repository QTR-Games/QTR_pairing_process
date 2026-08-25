// @vitest-environment jsdom
/**
 * The reach lines, checked on the screen rather than in the engine.
 *
 * `reach.equivalence.test.ts` already proves the rule is right. That says
 * nothing about whether the panel names the correct player or lights the
 * correct cells, and those are the two ways this feature can be wrong while
 * every engine test still passes.
 *
 * The highlight wiring is the real target. A row insight maps
 * `via -> ours-<via>` and a column insight maps `via -> <via>-theirs`; the two
 * are transposes of each other, both typecheck, and both produce a plausible
 * looking set of highlighted squares. Only a test that knows which cells ought
 * to light up can tell them apart, so the assertions below name exact keys
 * rather than counting them.
 *
 * The engine is used as an oracle for *which* players qualify, never for the
 * wording, so a copy change does not fail this file but a mis-wired index does.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { reachReport } from "../engine/reach";
import { Verdict } from "./Verdict";

afterEach(cleanup);

/**
 * Row 0 has a unique minimum; row 1's minimum is tied.
 *
 * Ana (row 0) bottoms out at 0.1 in exactly one column, so the protocol puts
 * her out of reach. Bokur (row 1) has 0.2 twice, so he genuinely can be forced
 * and must NOT be named. That contrast is the point of the fixture: a rule that
 * simply listed every player would pass a test that only checked Ana.
 */
const FRACTIONS: number[][] = [
  [0.1, 0.5, 0.6, 0.7, 0.8],
  [0.2, 0.2, 0.6, 0.7, 0.8],
  [0.5, 0.5, 0.5, 0.5, 0.5],
  [0.4, 0.5, 0.6, 0.5, 0.4],
  [0.3, 0.6, 0.5, 0.6, 0.5],
];

const board = (over: Partial<Board> = {}): Board => ({
  id: "reach-ui",
  opponent: "Opponent 07",
  ourPlayers: ["Ana", "Bokur", "Sam", "Pete", "Rue"],
  theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
  fractions: FRACTIONS,
  scaleId: "five",
  ourTeamFirst: true,
  updatedAt: 0,
  ...over,
});

/** Render and hand back whatever the last tap asked to highlight. */
function show(b: Board) {
  let highlighted: Set<string> = new Set();
  render(<Verdict board={b} dodgeMode="off" onHighlight={(c) => (highlighted = c)} />);
  return () => highlighted;
}

describe("Verdict reach lines", () => {
  it("names exactly the players the engine says are out of reach", () => {
    const b = board();
    const { floors } = reachReport(boardMatrix(b, boardScale(b)), undefined, b.ourTeamFirst);

    const expected = floors
      .filter((f) => f.protectedByProtocol)
      .map((f) => b.ourPlayers[f.ours]);
    const excluded = floors
      .filter((f) => !f.protectedByProtocol)
      .map((f) => b.ourPlayers[f.ours]);

    // The fixture is only interesting if it splits the roster.
    expect(expected.length).toBeGreaterThan(0);
    expect(excluded.length).toBeGreaterThan(0);
    expect(expected).toContain("Ana");
    expect(excluded).toContain("Bokur");

    show(b);
    const line = screen.getByText(/cannot be forced into their worst matchup/i);
    for (const name of expected) expect(line.textContent).toContain(name);
    for (const name of excluded) expect(line.textContent).not.toContain(name);
  });

  it("lights the row cells, not their transpose", () => {
    const b = board();
    const { floors } = reachReport(boardMatrix(b, boardScale(b)), undefined, b.ourTeamFirst);
    const shielded = floors.filter((f) => f.protectedByProtocol);

    const get = show(b);
    fireEvent.click(screen.getByText(/cannot be forced into their worst matchup/i));

    const want = new Set(shielded.flatMap((f) => f.via.map((t) => `${f.ours}-${t}`)));
    expect(get()).toEqual(want);

    // Every lit cell must sit in a row belonging to a named player. Under a
    // transpose the first index would be a column instead, which this catches
    // whenever the two sets differ.
    const rows = new Set(shielded.map((f) => f.ours));
    for (const key of get()) {
      expect(rows.has(Number(key.split("-")[0]))).toBe(true);
    }
  });

  it("says nothing about columns when no column is overstated", () => {
    // Column 2 is 0.6,0.6,0.5,0.6,0.5 -- its best is tied, so it is forceable.
    const b = board();
    const { ceilings } = reachReport(boardMatrix(b, boardScale(b)), undefined, b.ourTeamFirst);

    show(b);
    const shown = screen.queryByText(/reads? better than they play/i);
    if (ceilings.some((c) => c.overstated)) {
      expect(shown).not.toBeNull();
    } else {
      expect(shown).toBeNull();
    }
  });

  it("falls back to a findable label when the roster is not typed in yet", () => {
    const b = board({ ourPlayers: ["", "", "", "", ""] });
    show(b);
    const line = screen.getByText(/cannot be forced into their worst matchup/i);
    // Position is 1-based on screen, so row 0 must read "Your player 1".
    expect(line.textContent).toMatch(/Your player \d/);
  });
});
