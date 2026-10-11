/**
 * The numbers we are willing to print, pinned so they cannot drift.
 *
 * Everything asserted here is a figure used in public copy about what this app
 * does that a best-matching tool does not. Marketing claims rot quietly: the
 * engine improves, the fixture set grows, and a sentence written against one
 * set of numbers keeps being repeated against another. This file is the
 * one-click reproduction behind each sentence, so a claim that stops being
 * true fails CI instead of staying on a page.
 *
 * The comparison is between two ways of reading the same board:
 *
 *   - the ASSIGNMENT CEILING -- the best total over all 120 one-to-one
 *     matchings. This is what a tool that ranks permutations reports, and it is
 *     the score of a matching nobody has agreed to.
 *   - the PROTOCOL FLOOR -- the total that survives the actual nomination and
 *     decline sequence against an opponent playing their best. This is what you
 *     can hold no matter what they do.
 *
 * The ceiling is reachable only with the opponent's cooperation. The gap
 * between the two is the part of the plan that depends on them being helpful.
 *
 * Fixtures are the 31 real WTC 2024 boards in `__fixtures__/wtc2024Boards.json`,
 * anonymised at capture.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { assignmentExtremes, evenThreshold } from "./boardAnalysis";
import { protocolFloor } from "./protocol";
import { TEAM_SIZE } from "../model/board";

const FIXTURES = boards as { opponent: string; matrix: number[][] }[];

/** The dead-even line for a five-game round on the 1-5 scale: 15. */
const TAU = evenThreshold(TEAM_SIZE, 1, 5);

interface Read {
  opponent: string;
  ceiling: number;
  /** The floor available to whoever wins the dice-off and picks the better side. */
  floor: number;
  optimism: number;
}

function read(f: { opponent: string; matrix: number[][] }): Read {
  const [, ceiling] = assignmentExtremes(f.matrix);
  // The dice-off winner takes the better of the two sides, so the honest floor
  // for a board is the max, not whichever side we happened to default to.
  const floor = Math.max(
    protocolFloor(f.matrix, true).value,
    protocolFloor(f.matrix, false).value,
  );
  return { opponent: f.opponent, ceiling, floor, optimism: ceiling - floor };
}

describe("the claims we publish", () => {
  const reads = FIXTURES.map(read);
  const round2 = (x: number) => Math.round(x * 100) / 100;

  it("has the fixture set the claims are quoted against", () => {
    expect(FIXTURES).toHaveLength(31);
    expect(TAU).toBe(15);
  });

  it("the best-matching view overstates what you can hold", () => {
    const optimism = reads.map((r) => r.optimism);
    const summary = {
      mean: round2(optimism.reduce((a, b) => a + b, 0) / optimism.length),
      max: Math.max(...optimism),
      min: Math.min(...optimism),
    };

    /*
      Quoted as: "across 31 real WTC 2024 boards, the best-matching view
      overstates what you can actually hold by 1.45 points on average, and by
      as much as 3."
    */
    expect(summary).toEqual({ mean: 1.45, max: 3, min: 0 });
  });

  it("the ceiling is never below the floor, which is what makes it a gap", () => {
    // A negative optimism would mean the protocol guarantees a total no
    // matching achieves, which is impossible and would invalidate the framing
    // above rather than merely changing a number.
    for (const r of reads) {
      expect(r.optimism, r.opponent).toBeGreaterThanOrEqual(0);
      expect(r.floor, r.opponent).toBeLessThanOrEqual(r.ceiling);
    }
  });

  it("counts the boards that look won on paper and are not secured", () => {
    const looksWon = reads.filter((r) => r.ceiling > TAU && r.floor <= TAU);

    /*
      Quoted as: "22 of 31 look like a win on the matching view and are not
      actually secured."

      These are the boards where a permutation ranker shows a winning total
      while the guarantee is dead even or worse -- the specific failure the
      protocol view exists to catch.
    */
    expect(looksWon).toHaveLength(22);
  });
});
