/**
 * Who do we spend protection on, and how much did the board just cost us?
 *
 * ## Why this exists
 *
 * The worst-matchup dodge (`worstMatchupDodge`) answers "what is the single
 * cheapest bad cell to refuse". Measured against a captain actually driving the
 * app, that turned out to be the wrong question in two ways:
 *
 *  1. It names ONE cell by scan order and prices it, then stops. When a player
 *     picked up a *second* floor cell -- becoming materially harder to protect
 *     -- the headline did not move, because the global-minimum rating had not
 *     moved. The app looked frozen on a change that mattered.
 *
 *  2. It never says who is exposed. A single free dodge reads as "you're fine",
 *     when the real story on a stoplight board is "two of your five can be
 *     forced into a bad cell and you cannot keep them out of all of them".
 *
 * This module answers the captain's actual question -- *who can they trap, who
 * is already safe, and where do two of my players share a column* -- and pairs
 * it with the one number the old chip buried: our round-win chance, which moves
 * on every edit so a worsening board is visible instead of silent.
 *
 * ## Grounding
 *
 * The structural half is not a new search. `reach.ts` established -- measured on
 * 31 boards, 620 row/column observations, and re-checked against a solver on
 * every test run -- that a player's absolute worst matchup is refusable exactly
 * when it is UNIQUE in their row, and forceable exactly when it TIES. So
 * `forcedFloor().protectedByProtocol` already separates "safe" from "exposed"
 * for free, without the per-player constrained solve a first draft would reach
 * for. A scratch experiment on the owner's own board confirmed the equivalence
 * end to end: pricing each player's whole floor set with `avoidingWinChance`
 * reproduced exactly this split -- Dan/Pete/David (a unique worst) free to
 * protect, Rose/Amber (a tied worst) impossible to keep out of.
 *
 * The severity half is one `winChanceFloor` solve. On the owner's board that
 * number read 48.3%; dropping Rose from a tied {2,2} to a tied {1,1} -- deeper,
 * but structurally the same trap -- moved it to 44.8%. The classification was
 * unchanged (Rose was already exposed); the win chance was not. That 3.4-point
 * fall is the signal the old chip could not show, and the reason this read
 * carries the number rather than a rating.
 *
 * ## Cost
 *
 * `reachReport` is ten sorts of five numbers. `winChanceFloor` is a single
 * solve -- the same panel already runs `outlook`, which solves two dozen
 * sampled boards, on every render, so one more solve is inside the noise. There
 * is nothing here to gate, unlike the 25-cell `dodgeMapChance`.
 */

import { winChanceFloor } from "./avoidance";
import type { Matrix } from "./boardAnalysis";
import { reachReport } from "./reach";

/** One of our players, read as a protection target. */
export interface PlayerExposure {
  /** Index of our player, in board order. */
  ours: number;
  /** The lowest rating anywhere in their row. */
  rowWorst: number;
  /**
   * The worst rating the opponent can actually force on them. Equal to
   * `rowWorst` when exposed, one distinct rating better when safe.
   */
  forcedLevel: number;
  /** How many cells in the row sit at `rowWorst` -- the size of the trap. */
  floorCount: number;
  /**
   * Which protection tier this player sits in:
   *  - "exposed": their worst matchup ties in the row, so it cannot be refused
   *    and the opponent can drive them straight into it.
   *  - "shieldable": their worst is unique and therefore refusable, but the next
   *    cell they can be forced into is still below the midpoint -- keeping them
   *    out of the worst only concedes the next-worst. Protectable, not safe.
   *  - "safe": the worst they can actually be held to is at or above the
   *    midpoint; a nomination spent protecting them buys nothing.
   */
  status: "exposed" | "shieldable" | "safe";
  /**
   * True when `status === "exposed"`. Retained as a convenience for existing
   * call sites that only care about the tied-worst case.
   */
  exposed: boolean;
}

/** A their-side player whose column pressures two or more of ours at once. */
export interface JointColumn {
  /** Index of their player. */
  theirs: number;
  /** Our players rated below the midpoint against them, worst first. */
  ours: number[];
  /** The lowest rating any of those players holds in the column. */
  worst: number;
}

export interface ProtectionFocus {
  /** Our chance of taking the round with nothing refused. Moves on every edit. */
  base: number;
  /** The middle of the scale; the line below which a matchup counts as bad. */
  mid: number;
  /** Every one of our players, in board order. */
  players: PlayerExposure[];
  /** The exposed players, deepest forced floor first. The real risk list. */
  exposed: PlayerExposure[];
  /**
   * Players whose worst cell is refusable, yet whose next forced cell is still
   * below the midpoint. The protocol keeps them out of their worst only by
   * conceding the next-worst, so they read as "safe" but are not. Deepest
   * forced floor first.
   */
  shieldable: PlayerExposure[];
  /** Players the protocol holds at or above the midpoint -- genuinely safe. */
  safe: PlayerExposure[];
  /** Columns where one of their nominations threatens several of ours. */
  joint: JointColumn[];
  /**
   * The single player to weigh protection around first: the deepest, hardest
   * trap. Null when nobody is exposed. Not a promise that they can be saved --
   * an exposed player by definition cannot be fully dodged clear -- but the one
   * whose sequencing matters most.
   */
  focus: number | null;
  /**
   * The exposed players tied at the very top of the risk order -- same forced
   * floor and the same number of ways to force it -- so no free field can rank
   * one above another. `focus` is the first of them.
   *
   * Length tells the captain which decision he is in:
   *  - 0: nobody is exposed, there is no protect-first call to make.
   *  - 1: one player is unambiguously the deepest trap; protect around them.
   *  - 2+: a genuine tie. The engine cannot say who to spend on because they
   *    are equally exposed -- this is the owner's "I have to choose" moment,
   *    and naming one as "deepest" would be inventing a distinction that the
   *    numbers do not contain.
   */
  priorityTie: number[];
}

/**
 * Read the board as a protection problem.
 *
 * `ratingMin`/`ratingMax` and `ourTeamFirst` match the rest of the engine.
 * Reach is independent of who nominates first (measured), so `ourTeamFirst`
 * only reaches `winChanceFloor`, where it does matter.
 */
export function protectionFocus(
  matrix: Matrix,
  ratingMin = 1,
  ratingMax = 5,
  ourTeamFirst = true,
): ProtectionFocus {
  const n = matrix.length;
  const mid = (ratingMin + ratingMax) / 2;
  const base = winChanceFloor(matrix, ratingMin, ratingMax, ourTeamFirst);

  const { floors } = reachReport(matrix, undefined, ourTeamFirst);

  const players: PlayerExposure[] = floors.map((f) => {
    const floorCount = matrix[f.ours].filter((v) => v === f.rowWorst).length;
    // Three tiers off two numbers reach already measured, no solve:
    //  - forced floor at/above mid  -> genuinely safe.
    //  - forced floor still bad, worst refusable (`protectedByProtocol`)
    //    -> shieldable: you can dodge the worst but only into the next-worst.
    //  - forced floor still bad, worst tied (not refusable) -> exposed.
    // `protectedByProtocol` is reach's measured "unique worst is refusable" rule.
    const status: PlayerExposure["status"] =
      f.level >= mid ? "safe" : f.protectedByProtocol ? "shieldable" : "exposed";
    return {
      ours: f.ours,
      rowWorst: f.rowWorst,
      forcedLevel: f.level,
      floorCount,
      status,
      exposed: status === "exposed",
    };
  });

  const exposed = players
    .filter((p) => p.status === "exposed")
    // Deepest forced floor first; break ties toward the wider trap, then order.
    .sort(
      (a, b) => a.forcedLevel - b.forcedLevel || b.floorCount - a.floorCount || a.ours - b.ours,
    );

  const shieldable = players
    .filter((p) => p.status === "shieldable")
    // Deepest conceded floor first; then the wider spread of bad cells, then order.
    .sort(
      (a, b) => a.forcedLevel - b.forcedLevel || b.floorCount - a.floorCount || a.ours - b.ours,
    );

  const safe = players.filter((p) => p.status === "safe");

  const joint: JointColumn[] = [];
  for (let theirs = 0; theirs < n; theirs++) {
    const pressured: number[] = [];
    for (let ours = 0; ours < n; ours++) {
      if (matrix[ours][theirs] < mid) pressured.push(ours);
    }
    if (pressured.length >= 2) {
      pressured.sort((a, b) => matrix[a][theirs] - matrix[b][theirs] || a - b);
      joint.push({ theirs, ours: pressured, worst: matrix[pressured[0]][theirs] });
    }
  }
  // The column that squeezes the most players, deepest first, leads.
  joint.sort((a, b) => b.ours.length - a.ours.length || a.worst - b.worst || a.theirs - b.theirs);

  const focus = exposed.length > 0 ? exposed[0].ours : null;

  // The tie the free fields cannot break: everyone exposed who shares the
  // leader's forced floor AND trap width. Within the exposed set a player's
  // worst IS their forced floor, so (forcedLevel, floorCount) is the whole of
  // the measured priority key -- if two match on both, the ranking is a coin
  // flip and the UI must say "you choose" rather than pick for him.
  const priorityTie =
    exposed.length > 0
      ? exposed
          .filter(
            (p) =>
              p.forcedLevel === exposed[0].forcedLevel &&
              p.floorCount === exposed[0].floorCount,
          )
          .map((p) => p.ours)
      : [];

  return { base, mid, players, exposed, shieldable, safe, joint, focus, priorityTie };
}
