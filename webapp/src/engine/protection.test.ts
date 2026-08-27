/**
 * `protectionFocus` reframes the worst-matchup read from "cheapest cell to
 * refuse" into "who can be trapped, who is safe, and what did the board just
 * cost us". Two properties have to hold or the read is not worth trusting.
 *
 *  1. The structural split (exposed / shieldable / safe) must match `reach`'s
 *     measured rule -- a tied worst is forceable, a unique worst is not, and a
 *     unique worst whose next forced cell is still below the midpoint is
 *     protectable but not safe. This is the same equivalence a scratch
 *     experiment confirmed end to end against `avoidingWinChance` on the
 *     owner's board.
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

// A synthetic 1-5 board (midpoint 3) built to exercise all three tiers at once,
// including the case the 31 real fixtures never contain: a player with a doubled
// worst of 1. The owner told us this is the scenario he most fears -- "if a
// player has two 1's then they are harder to protect" -- and a board-by-board
// audit of every fixture found zero rows with a tied 1. Nothing in the repo
// drove `forcedLevel === 1` before this board, so the deepest-trap path went
// untested. Rows, in order:
//   0  [3,3,3,2,1]  unique worst 1, next forced cell a 2 -> shieldable
//   1  [3,3,3,1,1]  tied worst 1, unrefusable            -> exposed, forced 1
//   2  [3,3,4,3,3]  worst is a 3, at the midpoint        -> safe
//   3  [4,4,3,4,4]  worst is a 3, at the midpoint        -> safe
//   4  [5,4,5,4,5]  worst is a 4, above the midpoint     -> safe
const SCATTER: Matrix = [
  [3, 3, 3, 2, 1],
  [3, 3, 3, 1, 1],
  [3, 3, 4, 3, 3],
  [4, 4, 3, 4, 4],
  [5, 4, 5, 4, 5],
];

describe("protectionFocus", () => {
  it("splits the owner's board into exposed, shieldable, and genuinely safe", () => {
    const pf = protectionFocus(OWNER, 1, 10, false);

    // Rose (tied 2s) and Amber (tied 4s) can be forced into a bad cell.
    const exposedIdx = pf.exposed.map((p) => p.ours).sort((a, b) => a - b);
    expect(exposedIdx).toEqual([ROSE, AMBER]);

    // The other three each have a unique worst the protocol refuses -- but on
    // this middling board none of their forced floors clear the midpoint (5.5),
    // so all three are shieldable, not safe. The old exposed/safe binary read
    // them as "safe" and told the captain protecting them bought nothing.
    expect(pf.shieldable.map((p) => p.ours).sort((a, b) => a - b)).toEqual(
      [DAN, 1, 3].sort((a, b) => a - b),
    );
    expect(pf.safe).toHaveLength(0);

    const rose = pf.players[ROSE];
    expect(rose.exposed).toBe(true);
    expect(rose.status).toBe("exposed");
    expect(rose.floorCount).toBe(2);
    expect(rose.forcedLevel).toBe(2);

    // Dan's lone 1 is the lowest number on the board, yet it is refusable, so he
    // is not exposed. But refusing it only feeds him a 3, still below the
    // midpoint -- shieldable, not safe. This is exactly the case the old chip got
    // wrong, naming Dan's 1 and then going quiet as if he were fine.
    expect(pf.players[DAN].exposed).toBe(false);
    expect(pf.players[DAN].status).toBe("shieldable");
    expect(pf.players[DAN].forcedLevel).toBe(3);
    expect(pf.players[DAN].floorCount).toBe(1);
  });

  it("names the deepest, hardest trap as the focus", () => {
    const pf = protectionFocus(OWNER, 1, 10, false);
    // Rose and Amber are both exposed; Rose's floor (2) is deeper than Amber's
    // (4), so she is where sequencing matters most.
    expect(pf.focus).toBe(ROSE);
    // And she is unambiguously deepest -- Amber sits a whole tier higher -- so
    // the priority tie is just Rose. The captain is told who, not "you choose".
    expect(pf.priorityTie).toEqual([ROSE]);
  });

  it("hands back a genuine tie when two are equally exposed", () => {
    // 1-5 scale, midpoint 3, 4s filler so the only bad cells are the doubled 2s
    // under test. Players 0 and 1 each carry a tied worst of 2 (forced floor 2,
    // two ways to force it); the free (forcedLevel, floorCount) key cannot rank
    // one above the other, so the engine must not pretend it can.
    const tie: Matrix = [
      [4, 2, 4, 2, 4],
      [2, 4, 2, 4, 4],
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
      [4, 4, 4, 4, 4],
    ];
    const pf = protectionFocus(tie, 1, 5);

    expect(pf.exposed.map((p) => p.ours).sort((a, b) => a - b)).toEqual([0, 1]);
    for (const i of [0, 1]) {
      expect(pf.players[i].forcedLevel).toBe(2);
      expect(pf.players[i].floorCount).toBe(2);
    }
    // Both share the top of the risk order, so the tie carries both -- and the
    // UI reads "you choose" off a length of 2, not a named deepest player.
    expect(pf.priorityTie.slice().sort((a, b) => a - b)).toEqual([0, 1]);
    expect(pf.focus).toBe(0); // still a stable leader for back-compat call sites
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
    expect(pf.shieldable).toHaveLength(0);
    expect(pf.focus).toBeNull();
    expect(pf.priorityTie).toEqual([]);
    expect(pf.joint).toHaveLength(0);
  });

  it("carves the shieldable spread out of safe, and seats a doubled-1 in exposed", () => {
    const pf = protectionFocus(SCATTER, 1, 5);

    // Player 0 has a unique worst (a lone 1) that can be refused, so he is not
    // exposed -- but the next cell he can be forced into is a 2, still below the
    // midpoint of 3. He is shieldable: protectable, but not into anything good.
    expect(pf.players[0].status).toBe("shieldable");
    expect(pf.players[0].exposed).toBe(false);
    expect(pf.players[0].rowWorst).toBe(1);
    expect(pf.players[0].forcedLevel).toBe(2);
    expect(pf.shieldable.map((p) => p.ours)).toEqual([0]);

    // Player 1 has a doubled 1 -- a tied worst that cannot be refused -- so he is
    // exposed at a forced floor of 1. This is the owner's stated worst case, and
    // the first board in the suite to drive `forcedLevel === 1`.
    expect(pf.players[1].status).toBe("exposed");
    expect(pf.players[1].forcedLevel).toBe(1);
    expect(pf.players[1].floorCount).toBe(2);
    expect(pf.focus).toBe(1);
    expect(pf.exposed.map((p) => p.ours)).toEqual([1]);
    // One exposed player, so the priority tie is just him -- a clear leader.
    expect(pf.priorityTie).toEqual([1]);

    // The remaining three are held at or above the midpoint -- genuinely safe.
    expect(pf.safe.map((p) => p.ours).sort((a, b) => a - b)).toEqual([2, 3, 4]);
    expect(pf.players[2].status).toBe("safe");
  });
});
