// @vitest-environment jsdom
/**
 * The Board tab reads in round-win chance, and the threshold is gone.
 *
 * The old screen priced three of its four boxes in rating points and compared
 * each of them against `evenThreshold(5, min, max)` -- 15 on a 1-5 board, 27.5
 * on 1-10. That constant never moved for any board ever, so a captain reading
 * "the round needs 27.5" was reading a property of the scale, not a property of
 * the position, and paying a beat at the table for it.
 *
 * Priced in chance the same question is "is this over 50%", which needs no
 * constant on screen to parse. So the load-bearing assertion here is a negative
 * one, and it is deliberately stronger than "the string 15 is absent": the
 * boxes and the reading must contain no rating-point total AT ALL. A threshold
 * only earns its place next to a total, so keeping totals out of the decision
 * text is what actually stops it creeping back -- one helpful sentence
 * explaining what a number is measured against would restore the whole dead
 * constant, and nothing else in the suite would notice.
 *
 * Points are not gone from the screen, only demoted: they live in the note
 * under each box, which is asserted here too, because "we're on 15" is years of
 * habit for some captains and stranding them was never the goal.
 *
 * The rest holds the shape the reading depends on:
 *
 *   * the two Guaranteed paths agree about which side of the line we are on;
 *   * the boxes stay ordered guaranteed <= typical <= ceiling;
 *   * no percentage is printed to a decimal the model has not earned.
 *
 * Asserted against rendered text throughout, because every one of these can be
 * true in the engine and false on screen.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import boards from "../engine/__fixtures__/wtc2024Boards.json";
import { winChanceFloor } from "../engine/avoidance";
import { evenThreshold, type Matrix } from "../engine/boardAnalysis";
import { protocolFloor } from "../engine/protocol";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { Verdict } from "./Verdict";

afterEach(cleanup);

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

/**
 * A handful of real boards rather than all 31.
 *
 * Every render runs the sampled chance solve, so the full set would cost
 * minutes for assertions that are about wording and ordering rather than
 * coverage. These four span what the fixtures offer: comfortably ahead,
 * comfortably behind, and two nearer the middle.
 */
const SAMPLE = [FIXTURES[0], FIXTURES[7], FIXTURES[15], FIXTURES[24]];

/** The two scales the issue names, which are also the two tau values it names. */
const SCALES = ["five", "ten"] as const;

function toBoard(f: Fixture, scaleId: string = "five"): Board {
  return {
    id: `currency-${f.opponent}-${scaleId}`,
    opponent: f.opponent,
    ourPlayers: ["Ana", "Bokur", "Sam", "Pete", "Rue"],
    theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
    // Fixtures are stored on 1-5 and fractions are scale-free, so the same
    // board can be re-typed on any scale from them.
    fractions: f.matrix.map((row) => row.map((v) => (v - 1) / 4)),
    scaleId,
    ourTeamFirst: true,
    updatedAt: 0,
  };
}

/** The text a captain actually decides from: the three boxes and the reading. */
function decisionText(): string {
  const parts = [
    ...document.querySelectorAll(".stat-value"),
    ...document.querySelectorAll(".reading"),
  ];
  return parts.map((n) => n.textContent ?? "").join(" ");
}

/** Every run of digits in a string, carrying its percent sign if it has one. */
function numbers(text: string): string[] {
  return [...text.matchAll(/\d+(?:\.\d+)?%?/g)].map((m) => m[0]);
}

describe("Verdict reads in round-win chance", () => {
  it("puts no rating-point total in the boxes or the reading, on either scale", () => {
    // Which is what retires the threshold: with no totals on screen there is
    // nothing for a "needs 15" to sit beside. Every number a reader sees while
    // deciding must carry a percent sign.
    for (const scaleId of SCALES) {
      for (const f of SAMPLE) {
        cleanup();
        render(<Verdict board={toBoard(f, scaleId)} dodgeMode="off" />);
        const found = numbers(decisionText());
        expect(
          found.length,
          `${f.opponent} on ${scaleId} shows no numbers at all`,
        ).toBeGreaterThan(0);
        for (const n of found) {
          expect(n, `${f.opponent} on ${scaleId}: "${n}" is not a percentage`).toMatch(/%$/);
        }
      }
    }
  });

  it("never names the even threshold while deciding", () => {
    // Redundant given the test above, and kept anyway because it is the literal
    // ask in the issue and it names the constant. If that assertion is ever
    // loosened, this one still fails on the thing that mattered.
    for (const scaleId of SCALES) {
      const scale = boardScale(toBoard(SAMPLE[0], scaleId));
      const tau = evenThreshold(5, scale.min, scale.max);
      for (const f of SAMPLE) {
        cleanup();
        render(<Verdict board={toBoard(f, scaleId)} dodgeMode="off" />);
        expect(decisionText(), `${f.opponent} on ${scaleId}`).not.toContain(String(tau));
      }
    }
  });

  it("shows the guaranteed box as the chance floor, agreeing with the points floor", () => {
    // The issue asked for this to be confirmed before anything else. The box
    // that used to read "Round odds" and the box that read "Guaranteed" run the
    // same minimax over the same protocol, one accumulating points and one
    // accumulating three-of-five. They are one box now, so if the two paths
    // ever disagreed about which side of the line a board is on, the percentage
    // and the note beneath it would be describing different rounds.
    for (const f of SAMPLE) {
      const b = toBoard(f);
      const scale = boardScale(b);
      const matrix = boardMatrix(b, scale);
      const chanceFloor = winChanceFloor(matrix, scale.min, scale.max, true);
      const pointsFloor = protocolFloor(matrix, true).value;
      const tau = evenThreshold(5, scale.min, scale.max);

      expect(
        chanceFloor > 0.5,
        `${f.opponent}: chance floor ${chanceFloor} and points floor ${pointsFloor} disagree about the round`,
      ).toBe(pointsFloor > tau);

      cleanup();
      render(<Verdict board={b} dodgeMode="off" />);
      const box = screen.getByText("Guaranteed").parentElement!;
      expect(box.querySelector(".stat-value")!.textContent).toBe(
        `${Math.round(chanceFloor * 100)}%`,
      );
    }
  });

  it("keeps the points reading in the notes, so nobody is stranded", () => {
    // Demoted, not deleted. Both halves matter: the note carries a total AND
    // the denominator, because a bare "15" is exactly the number the threshold
    // used to have to explain.
    render(<Verdict board={toBoard(SAMPLE[0])} dodgeMode="off" />);
    for (const label of ["Guaranteed", "Typical", "Ceiling"]) {
      const box = screen.getByText(label).parentElement!;
      expect(box.querySelector(".stat-note")!.textContent, label).toMatch(/\d+(\.\d)? of 25\b/);
    }
  });

  it("orders the three boxes the way the reading claims they are ordered", () => {
    // The reading says guaranteed is what you hold if they hunt you, typical is
    // what happens when they do not, and the ceiling is the best still
    // reachable. Out of order those sentences describe a different board from
    // the one printed above them.
    for (const f of SAMPLE) {
      cleanup();
      render(<Verdict board={toBoard(f)} dodgeMode="off" />);
      const read = (label: string) =>
        Number(
          screen
            .getByText(label)
            .parentElement!.querySelector(".stat-value")!
            .textContent!.replace("%", ""),
        );
      const [floor, typical, ceiling] = ["Guaranteed", "Typical", "Ceiling"].map(read);
      expect(floor, f.opponent).toBeLessThanOrEqual(typical);
      expect(typical, f.opponent).toBeLessThanOrEqual(ceiling);
    }
  });

  it("rounds percentages to whole points rather than fabricating a tenth", () => {
    // SPREAD is an anchoring choice that has never been fitted against results,
    // so "62.4%" claims a precision the model does not have.
    for (const f of SAMPLE) {
      cleanup();
      render(<Verdict board={toBoard(f)} dodgeMode="off" />);
      expect(document.body.textContent ?? "", f.opponent).not.toMatch(/\d+\.\d+%/);
    }
  });

  it("says once what the percentages are and are not", () => {
    render(<Verdict board={toBoard(SAMPLE[0])} dodgeMode="off" />);
    expect(screen.getAllByText(/ordering between options, not as a forecast/i)).toHaveLength(1);
  });
});
