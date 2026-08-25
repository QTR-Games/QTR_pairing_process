/**
 * How far up and down the board can either side actually force play?
 *
 * ## The answer is a sort and a count
 *
 * This module used to run a constrained adversarial search per row and per
 * column. It no longer does, because the search was measured and found to
 * reproduce a two-line rule every single time:
 *
 *     a unique extreme moves one rung in; a tied extreme does not move at all.
 *
 * Swept over the 31 saved boards, all 155 rows and all 155 columns, in both
 * dice-off orientations -- 620 observations:
 *
 *     CEILING  columns with a unique max : 25  -> overstated  25 (100.0%)
 *              columns with a tied   max : 130 -> overstated   0   (0.0%)
 *              of those 25, level === 2nd distinct rating : 25 / 25
 *
 *     FLOOR    rows with a unique min    : 64  -> shielded   64 (100.0%)
 *              rows with a tied   min    : 91  -> shielded    0   (0.0%)
 *              of those 64, level === 2nd distinct rating : 64 / 64
 *
 * Perfect separation on both halves, and identical for `ourTeamFirst` true and
 * false: who nominates first does not move reach at all. `via` computed as
 * "every index at or above the level" matched the solver's own answer 620/620.
 *
 * ## Why this is not `pinReport` -- and why the first draft was
 *
 * `avoidance.ts` exports `canPin`, `isPinned` and `pinReport`, which answer
 * "can this player be driven into matchups above/below a threshold?" as a
 * boolean. Measured over the same boards at the midpoint threshold, the answer
 * is a constant: offensive pins achievable 154/155, defensive pins suffered
 * 0/155. A screen reporting "yes" 154 times out of 155 carries no information,
 * so more screen space was never what those three functions were missing.
 *
 * The threshold was what was missing, and sweeping it does produce a real
 * finding -- but the *first* version of this module drew that finding out of an
 * 8 ms search and then justified being desktop-only by the cost of that search.
 * That was the same mistake one level up. The finding survives; the expense
 * does not. Same answers, about a thousandth of the work.
 *
 * The mechanism is Finding 1 of `avoidance.ts` restated. A unique extreme is a
 * single cell, single cells are always dodgeable because leftover-becomes-
 * next-attacker always leaves an escape, so the level moves exactly one rung. A
 * tied extreme is a multi-cell same-row-or-column dodge, which never succeeds
 * on any board we hold, so the level does not move.
 *
 * ## What is still worth saying on screen
 *
 * "They cannot force your worst matchup when it is unique" is true, new, and
 * not visible anywhere else in the app -- 64 of 155 rows, two of your five
 * players on a typical board. Spending a nomination to protect those players
 * buys nothing. That claim is unchanged. Only its price tag changed.
 *
 * ## Trust
 *
 * The equivalence above is *measured on 31 boards, not proved*. The solver that
 * produced it is kept below as `forcedCeilingBySearch` / `forcedFloorBySearch`
 * and `reach.equivalence.test.ts` re-checks the cheap rule against it across
 * the full 620 on every run. If a future board breaks the rule the suite fails
 * loudly, rather than this module quietly lying on a screen.
 *
 * ## Currency
 *
 * Levels are ratings in the units on screen, so this is scale-free and never
 * compares a rating against a hardcoded number. Candidate levels are exactly
 * the distinct ratings already present in the row or column, which is both the
 * smallest sufficient set and the only one that cannot invent a level the board
 * does not use.
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
  /**
   * Always null. The points price of enforcing the level was only ever
   * available as a by-product of the search, and the search is gone. It was
   * measured at zero almost everywhere in any case -- a total is nearly
   * indifferent to which bad cell you eat. Kept on the type so callers that
   * destructure it still compile; `forcedCeilingBySearch` still populates it.
   */
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
 * If their column's best cell is unique we cannot insist on it -- they dodge
 * that one cell and we land on the next distinct rating down. If two or more of
 * our players tie for the best rating against them, they cannot dodge both, so
 * the column reads true.
 *
 * `base` and `ourTeamFirst` are accepted so the call site matches
 * `forcedCeilingBySearch`, which does consume them. Reach was measured to be
 * independent of both; see the module note.
 */
export function forcedCeiling(
  matrix: Matrix,
  theirs: number,
  _base?: number,
  _ourTeamFirst = true,
): ForcedCeiling {
  const column = matrix.map((row) => row[theirs]);
  const levels = columnLevels(matrix, theirs);
  const columnBest = levels[0];

  const unique = column.filter((v) => v === columnBest).length === 1;
  const level = unique && levels.length > 1 ? levels[1] : columnBest;

  const via: number[] = [];
  for (let ours = 0; ours < column.length; ours++) {
    if (column[ours] >= level) via.push(ours);
  }

  return { theirs, level, columnBest, via, price: null, overstated: level < columnBest };
}

/**
 * The worst rating they can force onto our player `ours`.
 *
 * The mirror of `forcedCeiling`. If the row's worst cell is unique we can
 * always refuse that one cell, so the floor is the next distinct rating up and
 * spending a nomination to protect this player buys nothing. If the row ties at
 * the bottom they can hold us to it.
 */
export function forcedFloor(
  matrix: Matrix,
  ours: number,
  _base?: number,
  _ourTeamFirst = true,
): ForcedFloor {
  const row = matrix[ours];
  const levels = rowLevels(matrix, ours);
  const rowWorst = levels[0];

  const unique = row.filter((v) => v === rowWorst).length === 1;
  const level = unique && levels.length > 1 ? levels[1] : rowWorst;

  const via: number[] = [];
  for (let theirs = 0; theirs < row.length; theirs++) {
    if (row[theirs] === level) via.push(theirs);
  }

  return { ours, level, rowWorst, via, protectedByProtocol: level > rowWorst };
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
 * Ten sorts of five numbers. Measured warm over the 31 saved boards at 0.008 ms
 * mean per board (0.34 ms on the very first call, before the JIT settles),
 * against 8.1 ms for the search it replaced under identical conditions -- about
 * a thousandfold. There is no longer any cost argument for showing this on one
 * screen size and not another.
 */
export function reachReport(matrix: Matrix, base?: number, ourTeamFirst = true): ReachReport {
  const n = matrix.length;
  const ceilings: ForcedCeiling[] = [];
  const floors: ForcedFloor[] = [];
  for (let i = 0; i < n; i++) {
    ceilings.push(forcedCeiling(matrix, i, base, ourTeamFirst));
    floors.push(forcedFloor(matrix, i, base, ourTeamFirst));
  }
  return { ceilings, floors };
}

/* ------------------------------------------------------------------------- *
 * Oracles.
 *
 * These are the original search-based implementations, kept only so
 * `reach.equivalence.test.ts` has something independent to check the cheap rule
 * against. They are not called by the app and should not be: they are roughly
 * 600x slower and, on every board measured so far, return the same answer.
 *
 * Do not delete them to tidy up. They are the reason the cheap rule is allowed
 * to be this cheap.
 * ------------------------------------------------------------------------- */

/**
 * `forcedCeiling` by constrained search.
 *
 * Walks the distinct ratings in their column from the top down and returns the
 * first level whose pin actually holds. Allowing only the cells at or above a
 * level is the same constraint as forbidding every cell below it, and a
 * complete pairing has to give them a partner from what remains.
 */
export function forcedCeilingBySearch(
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
 * `forcedFloor` by constrained search.
 *
 * Stated as its own negation, matching `isPinned`: walk the distinct ratings in
 * the row from the bottom up and return the first level we cannot refuse
 * outright. Everything below it is escapable, so that level is the floor.
 */
export function forcedFloorBySearch(
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
