/**
 * `protectionFocus` reframes the worst-matchup read from "cheapest cell to
 * refuse" into "who can be trapped, who is safe, and what did the board just
 * cost us". Two properties have to hold or the read is not worth trusting.
 *
 *  1. The structural split (exposed vs safe) must match `reach`'s measured rule
 *     -- a tied worst is forceable, a unique worst is not. This is the same
 *     equivalence a scratch experiment confirmed end to end against
 *     `avoidingWinChance` on the owner's board.
 *
 *  2. The severity number must move when the board genuinely worsens, because
 *     the entire reason this exists is that the old chip stayed silent on a
 *     change that mattered.
 *
 * The board below is the captain's own live grid, on the 1-10 scale, played
 * receive-first (`ourTeamFirst = false`). The numbers here are instance data
 * from that one board, not universal constants.
 */
import { describe, expect, it } from "vitest";
import type { Matrix } from "./boardAnalysis";
import { protectionFocus } from "./protection";

// Dan / Pete / Rose / David / Amber, versus opponents 1..5.
const OWNER: Matrix = [
  [1, 3, 5, 8, 6],
  [7, 5, 6, 4, 7],
  [2, 2, 9, 7, 6],
  [7, 8, 4, 5, 2],
  [6, 5, 7, 4, 4],
];

// The same board after Rose's two best-vs-worst cells are dragged down from a
// tied {2,2} to a tied {1,1}: a deeper trap, same shape.
const ROSE_DEEPER: Matrix = [
  [1, 3, 5, 8, 6],
  [7, 5, 6, 4, 7],
  [1, 1, 9, 7, 6],
  [7, 8, 4, 5, 2],
  [6, 5, 7, 4, 4],
];

const DAN = 0;
const ROSE = 2;
const AMBER = 4;

describe("protectionFocus", () => {
  it("splits the owner's board into the exposed and the already-safe", () => {
    const pf = protectionFocus(OWNER, 1, 10, false);

    // Rose (tied 2s) and Amber (tied 4s) can be forced into a bad cell; the
    // other three each have a unique worst the protocol refuses for them.
    const exposedIdx = pf.exposed.map((p) => p.ours).sort((a, b) => a - b);
    expect(exposedIdx).toEqual([ROSE, AMBER]);
    expect(pf.safe.map((p) => p.ours).sort((a, b) => a - b)).toEqual([1, 3, DAN].sort());

    const rose = pf.players[ROSE];
    expect(rose.exposed).toBe(true);
    expect(rose.floorCount).toBe(2);
    expect(rose.forcedLevel).toBe(2);

    // Dan's lone 1 is the lowest number on the board, yet he is NOT the risk:
    // a single worst cell is always refusable. This is exactly the case the old
    // chip got wrong, naming Dan and going quiet.
    expect(pf.players[DAN].exposed).toBe(false);
    expect(pf.players[DAN].floorCount).toBe(1);
  });

  it("names the deepest, hardest trap as the focus", () => {
    const pf = protectionFocus(OWNER, 1, 10, false);
    // Rose and Amber are both exposed; Rose's floor (2) is deeper than Amber's
    // (4), so she is where sequencing matters most.
    expect(pf.focus).toBe(ROSE);
  });

  it("finds the columns that squeeze more than one of our players", () => {
    const pf = protectionFocus(OWNER, 1, 10, false);
    // Opponent 2 is rated below the midpoint by Dan, Pete, Rose and Amber at
    // once -- one nomination, four players under pressure.
    const opp2 = pf.joint.find((j) => j.theirs === 1);
    expect(opp2).toBeDefined();
    expect(opp2?.ours.length).toBe(4);
    // The widest joint column leads the list.
    expect(pf.joint[0].theirs).toBe(1);
  });

  it("moves the win chance when the board worsens, even if the split does not", () => {
    const before = protectionFocus(OWNER, 1, 10, false);
    const after = protectionFocus(ROSE_DEEPER, 1, 10, false);

    // Rose stays exposed in both -- structurally the same trap...
    expect(before.players[ROSE].exposed).toBe(true);
    expect(after.players[ROSE].exposed).toBe(true);
    // ...but her forced floor deepens, and the round-win chance visibly falls.
    // This is the delta the old chip could not show.
    expect(after.players[ROSE].forcedLevel).toBe(1);
    expect(after.base).toBeLessThan(before.base);
    expect(before.base - after.base).toBeGreaterThan(0.02);

    // Sanity on the absolute figures measured for this board.
    expect(before.base).toBeCloseTo(0.4828, 2);
    expect(after.base).toBeCloseTo(0.4484, 2);
  });

  it("stays silent about protection on a comfortable board", () => {
    // Every cell above the middle of a 1-10 scale: nobody has a bad matchup, so
    // there is nobody to protect and nothing to warn about.
    const comfortable: Matrix = [
      [7, 8, 6, 7, 9],
      [8, 7, 7, 8, 6],
      [6, 8, 7, 7, 8],
      [7, 6, 8, 7, 7],
      [8, 7, 6, 8, 7],
    ];
    const pf = protectionFocus(comfortable, 1, 10, false);
    expect(pf.exposed).toHaveLength(0);
    expect(pf.focus).toBeNull();
    expect(pf.joint).toHaveLength(0);
  });
});
