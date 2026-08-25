/**
 * How far up and down the board can either side actually force play?
 *
 * ## Why this is not `pinReport`
 *
 * `avoidance.ts` exports `canPin`, `isPinned` and `pinReport`, which answer
 * "can this player be driven into matchups above/below a threshold?" as a
 * boolean. Measured over the 31 saved boards at the midpoint threshold, the
 * answer is a constant:
 *
 *     offensive pins achievable : 154 / 155
 *     defensive pins suffered   :   0 / 155
 *
 * That is not a defect in the solver. It is Finding 1 of `avoidance.ts` -- any
 * single cell is avoidable, because the leftover-becomes-next-attacker rule
 * always leaves an escape -- generalised to a set. A screen reporting "yes" 154
 * times out of 155 and "no" 155 times out of 155 carries no information, so
 * more screen space is not what those three functions were missing.
 *
 * The threshold is what was missing. Ask instead for the *highest* threshold
 * that still holds and the answer stops being a constant:
 *
 *     forced ceiling differs from the column maximum : 25 / 155 (16%)
 *     forced floor    differs from the row minimum   : 64 / 155 (41%)
 *
 * Those two lines are the whole point of this module. Reading a column and
 * taking its best cell overstates what you can actually get, one time in six.
 * Reading a row and taking its worst cell overstates the danger two times in
 * five -- the protocol protects you from your own worst matchup more often than
 * it exposes you to it, and nothing in the app has ever said so.
 *
 * ## Currency
 *
 * Levels are ratings in the units on screen, so this is scale-free and never
 * compares a rating against a hardcoded number. The candidate thresholds are
 * exactly the distinct ratings already present in the row or column being
 * searched, which is both the smallest sufficient set and the only one that
 * cannot invent a level the board does not use.
 *
 * Prices are carried through in points, and are usually zero for the reason
 * `winProbability.ts` sets out: a total is nearly indifferent to which bad cell
 * you eat. The *level* is the signal here, not the price.
 */

import { pinInto, priceCells, type Cell, type PinStatus } from "./avoidance";
import type { Matrix } from "./boardAnalysis";

/** The best matchup we can guarantee against one of their players. */
export interface ForcedCeiling {
  /** Index of their player. */
  theirs: number;
  /** Best rating we can force, or null if their column cannot be constrained. */
  level: number | null;
  /** Best rating visible in that column, ignoring whether it is reachable. */
  columnBest: number;
  /** Our players who can supply that guaranteed level. */
  via: number[];
  /** Points given up to enforce it. Usually zero; see the module note. */
  price: number | null;
  /** True when the grid promises more than the protocol can deliver. */
  overstated: boolean;
}

/** The worst matchup they can force onto one of our players. */
export interface ForcedFloor {
  /** Index of our player. */
  ours: number;
  /** Worst rating they can force on them. */
  level: number;
  /** Worst rating visible in that row, whether or not it is reachable. */
  rowWorst: number;
  /** Their players who could deliver that level. */
  via: number[];
  /** True when the row reads worse than the protocol allows them to make it. */
  protectedByProtocol: boolean;
}

/** Distinct ratings in a column, best first. */
const columnLevels = (matrix: Matrix, theirs: number): number[] =>
  [...new Set(matrix.map((row) => row[theirs]))].sort((a, b) => b - a);

/** Distinct ratings in a row, worst first. */
const rowLevels = (matrix: Matrix, ours: number): number[] =>
  [...new Set(matrix[ours])].sort((a, b) => a - b);

/**
 * The best rating we can guarantee against their player `theirs`.
 *
 * Walks the distinct ratings in their column from the top down and returns the
 * first level whose pin actually holds. `pinInto` does the work: allowing only
 * the cells at or above a level is the same constraint as forbidding every cell
 * below it, and a complete pairing has to give them a partner from what remains.
 */
export function forcedCeiling(
  matrix: Matrix,
  theirs: number,
  base: number,
  ourTeamFirst = true,
): ForcedCeiling {
  const levels = columnLevels(matrix, theirs);
  const columnBest = levels[0];

  for (const level of levels) {
    const allowed: number[] = [];
    for (let ours = 0; ours < matrix.length; ours++) {
      if (matrix[ours][theirs] >= level) allowed.push(ours);
    }
    const status: PinStatus = pinInto(matrix, theirs, allowed, base, ourTeamFirst);
    if (status.enforced !== null) {
      return {
        theirs,
        level,
        columnBest,
        via: allowed,
        price: status.price,
        overstated: level < columnBest,
      };
    }
  }

  // Unreachable on a complete board -- the bottom level allows every cell, so
  // the constraint is vacuous and always holds -- but a partially committed
  // board can strand a column, and null reads correctly as "nothing to force".
  return { theirs, level: null, columnBest, via: [], price: null, overstated: true };
}

/**
 * The worst rating they can force onto our player `ours`.
 *
 * Stated as its own negation, matching `isPinned`: we walk the distinct ratings
 * in the row from the bottom up and return the first level we cannot refuse
 * outright. Everything below it is escapable, so that level is the floor.
 */
export function forcedFloor(
  matrix: Matrix,
  ours: number,
  base: number,
  ourTeamFirst = true,
): ForcedFloor {
  const row = matrix[ours];
  const levels = rowLevels(matrix, ours);
  const rowWorst = levels[0];

  for (const level of levels) {
    const bad: Cell[] = [];
    for (let theirs = 0; theirs < row.length; theirs++) {
      if (row[theirs] <= level) bad.push({ ours, theirs });
    }
    // `avoided === null` means no strategy refuses every cell at or below this
    // level, so they can drive us here. The first such level is the floor.
    if (priceCells(matrix, bad, base, ourTeamFirst).avoided === null) {
      const via: number[] = [];
      for (let theirs = 0; theirs < row.length; theirs++) {
        if (row[theirs] === level) via.push(theirs);
      }
      return { ours, level, rowWorst, via, protectedByProtocol: level > rowWorst };
    }
  }

  // Refusing the whole row would leave our player without a partner, so the
  // loop always terminates above. Kept total for callers on partial boards.
  const top = levels[levels.length - 1];
  const via: number[] = [];
  for (let theirs = 0; theirs < row.length; theirs++) if (row[theirs] === top) via.push(theirs);
  return { ours, level: top, rowWorst, via, protectedByProtocol: top > rowWorst };
}

export interface ReachReport {
  /** One entry per player of theirs, in board order. */
  ceilings: ForcedCeiling[];
  /** One entry per player of ours, in board order. */
  floors: ForcedFloor[];
}

/**
 * Both readings for every player.
 *
 * Measured at 13.2 ms mean and 26.7 ms worst over the 31 saved boards, so this
 * is affordable on every render on a laptop. It is not affordable behind a
 * keystroke on a phone alongside everything else that screen already computes,
 * which is the honest reason it is desktop-only rather than a taste call.
 */
export function reachReport(matrix: Matrix, base: number, ourTeamFirst = true): ReachReport {
  const n = matrix.length;
  const ceilings: ForcedCeiling[] = [];
  const floors: ForcedFloor[] = [];
  for (let i = 0; i < n; i++) {
    ceilings.push(forcedCeiling(matrix, i, base, ourTeamFirst));
    floors.push(forcedFloor(matrix, i, base, ourTeamFirst));
  }
  return { ceilings, floors };
}
