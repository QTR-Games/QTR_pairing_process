// @vitest-environment jsdom
/**
 * "Too close to call", on the screen rather than in the engine.
 *
 * `chance.expected` is a Monte Carlo mean over 24 sampled opponent boards, and
 * Verdict branches on it: `expected > 0.5` chooses between "this is a round you
 * take by playing for the win" and "the win has to come from the ceiling -- it
 * needs them to give you something". Those are opposite instructions.
 *
 * measure.outlookNoise priced that comparison against a 4000-trial reference on
 * the 31 saved boards, back when the screen read in points: 5 sat closer to the
 * line than the sampling error and one sat exactly on it at 0.000. So on
 * roughly a board in six, which instruction the app gave was decided by the
 * random draw.
 *
 * The fix is for the estimate to carry its own error bar and for the comparison
 * to decline when the gap is inside it. This file asserts the screen actually
 * declines -- and, just as importantly, that it still commits everywhere else,
 * because a guard that fires too often is its own failure.
 *
 * ## Why a constructed board sits alongside the saved ones
 *
 * Moving the reading into round-win chance made the guard fire LESS, not more:
 * none of the 31 saved boards now lands inside its own error bar, where one did
 * in points. That is the currency doing its job -- a total is nearly
 * indifferent to which cells make it up, so boards that points could not
 * separate from an even round are separated by three-of-five -- but it leaves
 * the guard untested by real data, and an untested guard is indistinguishable
 * from a dead one.
 *
 * So ON_THE_LINE is a board built to sit there, and the file asserts both
 * halves: the constructed board hedges, and all 31 real ones get a straight
 * answer.
 *
 * The engine is used as an oracle for the PRECONDITION only. Which boards are
 * close is read from `chanceOutlook`; what the screen says about them is
 * asserted against the rendered text.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import boards from "../engine/__fixtures__/wtc2024Boards.json";
import { winChanceFloor } from "../engine/avoidance";
import { evenThreshold, decisionReport, SECURED, UNWINNABLE, type Matrix } from "../engine/boardAnalysis";
import { chanceOutlook } from "../engine/opponent";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { Verdict } from "./Verdict";

afterEach(cleanup);

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

/**
 * A board that genuinely sits on the line, found by search rather than guessed.
 *
 * Its typical round-win chance lands well inside its own two-error band, while
 * the guaranteed reading is 34%, so the screen reaches the hedge rather than
 * short-circuiting on "guaranteed wins it" above. It is a plausible board, not
 * a pathological one: mostly 2s and 3s with a couple of good matchups, which is
 * what half the sheets at an event look like.
 */
const ON_THE_LINE: Fixture = {
  opponent: "On the line",
  matrix: [
    [2, 4, 3, 2, 2],
    [4, 3, 2, 2, 2],
    [3, 3, 3, 3, 3],
    [2, 3, 3, 2, 2],
    [3, 2, 2, 3, 2],
  ],
};

const FIXTURES = [...(boards as Fixture[]), ON_THE_LINE];

/**
 * The saved fixtures are rating matrices; a Board stores fractions. On the
 * "five" scale a rating is `1 + 4f`, so this is that inverted. Going through
 * the real Board shape matters -- it is what Verdict is handed at runtime.
 */
const toBoard = (f: Fixture): Board => ({
  id: `close-${f.opponent}`,
  opponent: f.opponent,
  ourPlayers: ["Ana", "Bokur", "Sam", "Pete", "Rue"],
  theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
  fractions: f.matrix.map((row) => row.map((v) => (v - 1) / 4)),
  scaleId: "five",
  ourTeamFirst: true,
  updatedAt: 0,
});

/**
 * How far this board sits from the decision edge, in units of its own error bar
 * -- plus whether the hedge is even reachable on it.
 *
 * The reachability half was an omission first time round and the test caught it
 * twice, which is the value of asserting against the screen instead of the
 * engine. Verdict resolves three questions before it ever consults the typical
 * case, and each of them settles the round outright:
 *
 *   UNWINNABLE        the ceiling cannot reach the round
 *   SECURED           the floor already takes it
 *   guaranteed > 50%  playing properly takes it whatever they do
 *
 * On any of those there is nothing to be uncertain about, so the hedge must not
 * fire however close the Monte Carlo mean happens to land. Mirroring the real
 * ordering here is what makes the third test -- "still commits everywhere
 * else" -- mean something rather than pass by luck.
 */
function edgeDistance(f: Fixture): { gap: number; band: number; reachable: boolean } {
  const b = toBoard(f);
  const scale = boardScale(b);
  const matrix = boardMatrix(b, scale);
  const n = matrix.length;
  const guaranteed = winChanceFloor(matrix, scale.min, scale.max, true);
  const tau = evenThreshold(b.ourPlayers.length, scale.min, scale.max);
  const verdict = decisionReport(matrix, tau).board.verdict;
  const o = chanceOutlook(
    matrix,
    { ourPool: (1 << n) - 1, theirPool: (1 << n) - 1, attacker: -1, attackerSide: "our" },
    guaranteed,
    scale.min,
    scale.max,
  );
  return {
    gap: Math.abs(o.expected - 0.5),
    band: 2 * o.stderr,
    reachable: verdict !== UNWINNABLE && verdict !== SECURED && guaranteed <= 0.5,
  };
}

const scored = FIXTURES.map((f) => ({ f, ...edgeDistance(f) }));
const onTheLine = scored.filter((s) => s.reachable && s.gap < s.band);
const clearOfIt = scored.filter((s) => !s.reachable || s.gap >= s.band);

/** The phrase the guard adds. Meaning, not wording -- kept to one clause. */
const HEDGE = /too close to call/i;

describe("Verdict declines to guess when the estimate cannot tell", () => {
  it("has real boards on both sides, or this file proves nothing", () => {
    // A guard that never fires and a guard that always fires look identical
    // from a passing test suite. This is the check that the fixtures actually
    // exercise both branches.
    expect(onTheLine.length, "no saved board sits inside its own error bar").toBeGreaterThan(0);
    expect(clearOfIt.length).toBeGreaterThan(0);
  });

  it("says so on every board whose gap is inside its error bar", () => {
    for (const s of onTheLine) {
      cleanup();
      render(<Verdict board={toBoard(s.f)} dodgeMode="off" />);
      expect(
        screen.getByText(HEDGE),
        `${s.f.opponent}: gap ${s.gap.toFixed(3)} inside band ${s.band.toFixed(3)}`,
      ).toBeTruthy();
    }
  });

  it("still commits on the boards that are not close, rather than hedging everything", () => {
    for (const s of clearOfIt) {
      cleanup();
      render(<Verdict board={toBoard(s.f)} dodgeMode="off" />);
      expect(
        screen.queryByText(HEDGE),
        `${s.f.opponent}: gap ${s.gap.toFixed(3)} is outside band ${s.band.toFixed(3)} and should get a straight answer`,
      ).toBeNull();
    }
  });

  it("hedges on a small minority of boards, not most of them", () => {
    // The guard exists to stop the app being confidently wrong, not to stop it
    // being useful. If it swallowed most boards it would be a worse failure
    // than the one it fixes.
    expect(onTheLine.length).toBeLessThan(FIXTURES.length / 3);
  });

  it("gives a straight answer on all 31 real boards", () => {
    // Recorded rather than assumed. Chance separates boards that points could
    // not, so nothing saved lands on the line any more; if a change to the
    // model or the trial count starts pulling real boards back onto it, this is
    // where it shows up and the docstring above stops being true.
    expect(onTheLine.map((s) => s.f.opponent)).toEqual([ON_THE_LINE.opponent]);
  });
});
