/**
 * Which matchups can you refuse, and what does refusing cost?
 *
 * ## Why this module exists
 *
 * `protocol.ts` answers "what total can I guarantee?". That is the right
 * question for a verdict and the wrong question at the moment of a decision,
 * because it collapses the board to one number and throws away the thing a
 * captain is actually arguing about: *we cannot let Dave play into that list.*
 *
 * Two measurements motivate what follows. Both enumerate the real protocol
 * tree over 45 saved boards from past events.
 *
 * 1. **Any single cell is avoidable.** On every board, whether we open or they
 *    do, a strategy exists that guarantees a chosen matchup never happens. This
 *    is a property of the turn-taking rules, not of the ratings -- the
 *    leftover-becomes-next-attacker rule always leaves an escape. One bad
 *    rating therefore cannot lose a round on its own.
 *
 * 2. **Avoiding it is usually, but not always, free.** Priced as lost round-win
 *    probability: free on 36 of 45 boards, mean 0.610%, worst 7.969%. Avoiding
 *    the worst TWO at once is only possible on 31 of 45, and costs up to
 *    11.262% where it is.
 *
 * The gap between those two facts is the entire point. Four boards in five, the
 * dodge is a formality and deserves none of the fifteen minutes a round allows.
 * The fifth is a real trade that deserves most of them. Nothing in the app
 * currently distinguishes the two cases, so every dodge gets argued from
 * scratch and the expensive ones get argued no harder than the free ones.
 *
 * ## What "price" means here
 *
 * Price is expressed in the board's own rating units, so it is scale-free: a
 * 1-3 board, a 1-5 board and a 1-10 board all report a price in the units their
 * players typed. It is the drop in the *guaranteed* total -- what you give up
 * in the worst case, not what you expect to give up.
 *
 * That is deliberately the pessimistic reading. Finding 16 measured the
 * guarantee as running 1.40 points below realised results. A price computed
 * this way is therefore an upper bound on what the dodge costs you, which is
 * the correct direction for a number that talks someone out of a safety move.
 *
 * ## The opponent
 *
 * Identical to `protocol.ts`: they minimise our total on our own numbers, and
 * for the avoidance constraint they are assumed to *want* the forbidden cell.
 * Both are bounds rather than beliefs. Finding 12 killed the mirror axiom
 * (r = -0.049 over 25 shared matchups), so we do not claim to know what they
 * want; we only claim they cannot hurt us more than the worst they could do.
 */

import type { Matrix } from "./boardAnalysis";
import type { ProtocolState, Side } from "./protocol";
import { atLeast, extendDistribution, probabilityMatrix, winsNeeded } from "./winProbability";

/** A single matchup: OUR player `ours` against THEIR player `theirs`. */
export interface Cell {
  ours: number;
  theirs: number;
}

/**
 * What it costs to guarantee a matchup never happens.
 *
 * `price` and `avoided` are `null` exactly when the cell is unavoidable, which
 * for a single cell never occurs on a full board but does occur once some
 * pairings are already committed.
 */
export interface DodgePrice {
  cell: Cell;
  /** The rating in that cell, carried through for display. */
  rating: number;
  /** Guaranteed total with no constraint. */
  base: number;
  /** Guaranteed total among strategies that refuse the cell. */
  avoided: number | null;
  /** `base - avoided`. Non-negative. */
  price: number | null;
  /** True when the constraint costs nothing at all. */
  free: boolean;
}

/**
 * Cells encode as a bit index so a forbidden set is one integer, which keeps
 * the hot recursion free of allocation and set lookups.
 */
export const cellBit = (cell: Cell, n: number): number => 1 << (cell.ours * n + cell.theirs);

export const forbidCells = (cells: readonly Cell[], n: number): number =>
  cells.reduce((mask, c) => mask | cellBit(c, n), 0);

const isForbidden = (mask: number, ours: number, theirs: number, n: number): boolean =>
  (mask & (1 << (ours * n + theirs))) !== 0;

const bits = (mask: number): number[] => {
  const out: number[] = [];
  for (let i = 0; mask >> i; i++) if (mask & (1 << i)) out.push(i);
  return out;
};

const popcount = (mask: number): number => bits(mask).length;

/**
 * Minimax value of a state among strategies that never reach a forbidden cell.
 *
 * `null` means the constraint cannot be met: the opponent can force one of the
 * forbidden matchups no matter what we do.
 *
 * The propagation rule is what makes this a guarantee rather than a hope. At a
 * node we own, we may choose any child that is not `null`, so `null` children
 * are simply skipped. At a node they own, they are assumed to take a `null`
 * child if one exists -- so a single unmeetable branch poisons the whole node.
 * Read plainly: we need one way through, they need one way in.
 *
 * Mirrors `solveProtocol` in ./protocol.ts step for step. The two must stay
 * structurally identical; `avoidance.test.ts` pins them together by asserting
 * that an empty forbidden set reproduces `protocolFloor` exactly.
 */
export function solveAvoiding(
  matrix: Matrix,
  state: ProtocolState,
  forbidden: number,
  memo: Map<string, number | null> = new Map(),
): number | null {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const n = matrix.length;
  const key = `${ourPool}|${theirPool}|${attacker}|${attackerSide}`;
  if (memo.has(key)) return memo.get(key) as number | null;

  let result: number | null;

  if (attacker < 0) {
    // Opening: we put a player forward, so we may choose any viable one.
    let best: number | null = null;
    for (const p of bits(ourPool)) {
      const sub = solveAvoiding(
        matrix,
        { ourPool: ourPool & ~(1 << p), theirPool, attacker: p, attackerSide: "our" },
        forbidden,
        memo,
      );
      if (sub !== null && (best === null || sub > best)) best = sub;
    }
    memo.set(key, best);
    return best;
  }

  const offeringPool = attackerSide === "our" ? theirPool : ourPool;
  const candidates = bits(offeringPool);

  if (candidates.length === 0) {
    memo.set(key, 0);
    return 0;
  }

  if (candidates.length === 1) {
    // Forced pairing. No decision remains, so a forbidden cell here is fatal.
    const other = candidates[0];
    const [ours, theirs] = attackerSide === "our" ? [attacker, other] : [other, attacker];
    result = isForbidden(forbidden, ours, theirs, n) ? null : matrix[ours][theirs];
    memo.set(key, result);
    return result;
  }

  const defenderIsUs = attackerSide === "their";
  let chosen: number | null = null;
  let sawUnmeetable = false;

  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const value = resolveOfferAvoiding(
        matrix,
        state,
        [candidates[a], candidates[b]],
        forbidden,
        memo,
      );
      if (value === null) {
        // They will offer this pair precisely because we cannot survive it.
        if (!defenderIsUs) {
          sawUnmeetable = true;
        }
        continue;
      }
      if (chosen === null) chosen = value;
      else if (defenderIsUs ? value > chosen : value < chosen) chosen = value;
    }
    if (sawUnmeetable) break;
  }

  result = sawUnmeetable ? null : chosen;
  memo.set(key, result);
  return result;
}

/**
 * Value of one offer once the attacking side picks from it.
 *
 * The declined player becomes their own side's next attacker, which is the rule
 * that makes a bus possible and the reason avoidance has to be searched rather
 * than reasoned about a cell at a time.
 */
function resolveOfferAvoiding(
  matrix: Matrix,
  state: ProtocolState,
  pair: [number, number],
  forbidden: number,
  memo: Map<string, number | null>,
): number | null {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const n = matrix.length;
  const attackerIsUs = attackerSide === "our";
  let best: number | null = null;

  for (const picked of pair) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];

    if (isForbidden(forbidden, ours, theirs, n)) {
      // They would take this pick to land the cell we are refusing.
      if (!attackerIsUs) return null;
      continue;
    }

    const nextOurPool = attackerIsUs ? ourPool : ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheirPool = attackerIsUs
      ? theirPool & ~(1 << picked) & ~(1 << leftover)
      : theirPool;

    const exhausted = popcount(nextOurPool) === 0 && popcount(nextTheirPool) === 0;
    const rest = exhausted
      ? 0
      : solveAvoiding(
          matrix,
          {
            ourPool: nextOurPool,
            theirPool: nextTheirPool,
            attacker: leftover,
            attackerSide: attackerIsUs ? "their" : "our",
          },
          forbidden,
          memo,
        );

    if (rest === null) {
      if (!attackerIsUs) return null;
      continue;
    }

    const total = matrix[ours][theirs] + rest;
    if (best === null) best = total;
    else if (attackerIsUs ? total > best : total < best) best = total;
  }

  return best;
}

/**
 * Guaranteed total among strategies that refuse every cell in `forbidden`.
 *
 * `null` means no such strategy exists. With `ourTeamFirst = false` they open,
 * and they open with whichever player is worst for us -- the same convention
 * `protocolFloor` uses, so the two numbers are directly comparable.
 */
export function avoidingFloor(
  matrix: Matrix,
  forbidden: number,
  ourTeamFirst = true,
): number | null {
  const n = matrix.length;
  const full = (1 << n) - 1;

  if (ourTeamFirst) {
    return solveAvoiding(
      matrix,
      { ourPool: full, theirPool: full, attacker: -1, attackerSide: "our" },
      forbidden,
    );
  }

  const memo = new Map<string, number | null>();
  let worst: number | null = null;
  for (let p = 0; p < n; p++) {
    const sub = solveAvoiding(
      matrix,
      {
        ourPool: full,
        theirPool: full & ~(1 << p),
        attacker: p,
        attackerSide: "their" as Side,
      },
      forbidden,
      memo,
    );
    // They open with the player worst for us, including one we cannot survive.
    if (sub === null) return null;
    if (worst === null || sub < worst) worst = sub;
  }
  return worst;
}

/** Price of refusing a set of cells together, given an already-known `base`. */
export function priceCells(
  matrix: Matrix,
  cells: readonly Cell[],
  base: number,
  ourTeamFirst = true,
): { avoided: number | null; price: number | null; free: boolean } {
  const avoided = avoidingFloor(matrix, forbidCells(cells, matrix.length), ourTeamFirst);
  if (avoided === null) return { avoided: null, price: null, free: false };
  const price = base - avoided;
  return { avoided, price, free: price < 1e-9 };
}

/**
 * The price of refusing each matchup on the board, one at a time.
 *
 * Sorted cheapest first, so the head of the list is the set of matchups you can
 * strike out at no cost and the tail is the set worth arguing about. This is
 * the ordering the measurement says matters: the expensive tail is a fifth of
 * boards, and it is invisible in a single guaranteed total.
 *
 * `n^2` solves of a tree with a few thousand leaves. Measured well under a
 * frame on a 5x5 board; `measure.avoidance.test.ts` guards the budget.
 */
export function dodgeMap(matrix: Matrix, base: number, ourTeamFirst = true): DodgePrice[] {
  const n = matrix.length;
  const out: DodgePrice[] = [];
  for (let ours = 0; ours < n; ours++) {
    for (let theirs = 0; theirs < n; theirs++) {
      const cell: Cell = { ours, theirs };
      const { avoided, price, free } = priceCells(matrix, [cell], base, ourTeamFirst);
      out.push({ cell, rating: matrix[ours][theirs], base, avoided, price, free });
    }
  }
  out.sort((a, b) => {
    if (a.price === null) return b.price === null ? 0 : 1;
    if (b.price === null) return -1;
    return a.price - b.price || a.rating - b.rating;
  });
  return out;
}

/**
 * Can both of these be refused by one strategy, and at what cost?
 *
 * Avoidance does not compose: each of the worst two cells is individually
 * dodgeable on every board, yet a single strategy dodges both on only 31 of 45.
 * A UI that prices dodges one at a time will therefore promise two escapes it
 * cannot deliver together, which is why this is a separate call rather than a
 * sum over `dodgeMap`.
 */
export function pricePair(
  matrix: Matrix,
  a: Cell,
  b: Cell,
  base: number,
  ourTeamFirst = true,
): DodgePrice & { second: Cell } {
  const { avoided, price, free } = priceCells(matrix, [a, b], base, ourTeamFirst);
  return {
    cell: a,
    second: b,
    rating: matrix[a.ours][a.theirs],
    base,
    avoided,
    price,
    free,
  };
}

/**
 * Whether a player can be driven into a named set of matchups, and what it costs.
 *
 * `enforced` is `null` exactly when no strategy achieves it against best play.
 */
export interface PinStatus {
  /** Row index for a defensive pin, column index for an offensive one. */
  player: number;
  /** The matchups the pin drives play into. */
  cells: Cell[];
  /** Guaranteed total among strategies that enforce the pin. */
  enforced: number | null;
  /** `base - enforced`. Non-negative; `null` when unenforceable. */
  price: number | null;
  /** True when enforcing costs nothing at all. */
  free: boolean;
}

/**
 * Forcing is avoidance wearing a different hat.
 *
 * To drive their player `theirs` into the set `allowedOurs`, forbid every other
 * cell in their column. A complete pairing has to give them a partner, and the
 * only partners left are the ones we chose -- so the pin holds exactly when the
 * derived avoidance holds. That identity is why this needs no second solver:
 * `solveAvoiding` already carries the pools, the memo and the null-propagation
 * that make the claim survive the protocol rather than merely describe the grid.
 *
 * An empty `allowedOurs` forbids the whole column, no complete pairing exists,
 * and the solver returns `null` -- which reads correctly as "cannot be pinned".
 */
export function pinInto(
  matrix: Matrix,
  theirs: number,
  allowedOurs: readonly number[],
  base: number,
  ourTeamFirst = true,
): PinStatus {
  const n = matrix.length;
  const allowed = new Set(allowedOurs);
  const forbidden: Cell[] = [];
  for (let ours = 0; ours < n; ours++) {
    if (!allowed.has(ours)) forbidden.push({ ours, theirs });
  }
  const cells = allowedOurs.map((ours) => ({ ours, theirs }));
  const { avoided, price, free } = priceCells(matrix, forbidden, base, ourTeamFirst);
  return { player: theirs, cells, enforced: avoided, price, free };
}

/**
 * The offensive pin: can we force their player into a matchup we favour?
 *
 * This is the column reading -- *how many of ours beat that one of theirs* --
 * and it is deliberately not the row reading the desktop grid used to show.
 * Counting favourable cells in a column says only that good matchups exist on
 * paper; it cannot say whether the turn order lets us reach one. Here a `PIN`
 * means the pairing lands there against any defence.
 */
export function canPin(
  matrix: Matrix,
  theirs: number,
  threshold: number,
  base: number,
  ourTeamFirst = true,
): PinStatus {
  const favourable: number[] = [];
  for (let ours = 0; ours < matrix.length; ours++) {
    if (matrix[ours][theirs] > threshold) favourable.push(ours);
  }
  return pinInto(matrix, theirs, favourable, base, ourTeamFirst);
}

/**
 * The defensive pin: can they force our player into a matchup we lose?
 *
 * Stated as its own negation, because that is the version the solver answers
 * directly: we are pinned when no strategy refuses every bad cell in our row.
 * When escape *is* possible, `price` is what the escape costs, which is the
 * number worth arguing about and the one a cell count could never produce.
 */
export function isPinned(
  matrix: Matrix,
  ours: number,
  threshold: number,
  base: number,
  ourTeamFirst = true,
): PinStatus & { pinned: boolean } {
  const n = matrix.length;
  const bad: Cell[] = [];
  for (let theirs = 0; theirs < n; theirs++) {
    if (matrix[ours][theirs] < threshold) bad.push({ ours, theirs });
  }
  const { avoided, price, free } = priceCells(matrix, bad, base, ourTeamFirst);
  return {
    player: ours,
    cells: bad,
    enforced: avoided,
    price,
    free,
    // No bad cells at all is safety, not a pin.
    pinned: bad.length > 0 && avoided === null,
  };
}

/**
 * Both pins for every player, ready for display.
 *
 * `threshold` is supplied by the caller rather than assumed, which is what keeps
 * this correct on 1-3, 1-5 and 1-10 boards alike; `evenThreshold` in
 * ./boardAnalysis derives it from the scale in use.
 */
export function pinReport(
  matrix: Matrix,
  threshold: number,
  base: number,
  ourTeamFirst = true,
): { offense: PinStatus[]; defense: (PinStatus & { pinned: boolean })[] } {
  const n = matrix.length;
  const offense: PinStatus[] = [];
  const defense: (PinStatus & { pinned: boolean })[] = [];
  for (let i = 0; i < n; i++) {
    offense.push(canPin(matrix, i, threshold, base, ourTeamFirst));
    defense.push(isPinned(matrix, i, threshold, base, ourTeamFirst));
  }
  return { offense, defense };
}

// ---------------------------------------------------------------------------
// Probability-valued avoidance
// ---------------------------------------------------------------------------

/**
 * ## Why everything above this line reads 0.000
 *
 * `dodgeMap` prices a refusal in points and reports `free: true` on every cell
 * of every fixture board. That is not a bug and it is not a discovery -- it is
 * what happens when you ask an additive objective which of two bad cells you
 * would rather eat. The sum does not care. Swap a 9 and a 1 for two 5s and the
 * guaranteed total is unchanged, so a search that maximises the total is
 * genuinely indifferent, and reports the indifference honestly.
 *
 * The decision is not indifferent. A round is taken by winning three of five,
 * and 5-5-5-5-5 wins a round far more often than 9-9-1-1-1 despite the equal
 * total. Under P(>= 3 wins) the same dodges that priced at zero price at up to
 * 7.969% (measured over 45 saved boards, `files/probe_dodge_price.py`).
 *
 * So this section gives the avoidance search its own value function. The
 * app-wide objective is untouched: the verdict, the threshold and the sort all
 * still run on points. Only the question "what does this refusal cost?" is
 * answered in the currency that actually decides the round.
 *
 * ## Why this is a separate search rather than a swapped constant
 *
 * The points search accumulates: `value(node) = cell + value(child)`. That is
 * what lets it memoise on the pools alone, because the future is independent of
 * the past.
 *
 * P(>= 3) does not accumulate. Whether one more win matters depends entirely on
 * how many are already banked, so the value of a subtree depends on the path
 * taken to reach it. The search therefore carries the distribution of wins so
 * far and evaluates only at a complete assignment, and the memo key includes
 * that distribution.
 *
 * The tempting shortcut -- carry "wins still needed" as an integer and take
 * `p * V(need-1) + (1-p) * V(need)` -- is WRONG, and worth naming so it is not
 * reintroduced as an optimisation. It presumes the two terms may be achieved by
 * different strategies, when one strategy has to serve both. It would overstate
 * our chances by exactly the amount that hindsight is worth.
 *
 * The cost of doing it properly is bounded: at a given pool state the
 * distribution depends only on the multiset of probabilities already fixed, so
 * distinct paths that fixed the same values share a memo entry.
 */

/** Distribution signature for the memo key. Rounded to keep float noise out. */
const distKey = (dist: readonly number[]): string => {
  let out = "";
  for (let i = 0; i < dist.length; i++) out += (i ? "," : "") + dist[i].toFixed(9);
  return out;
};

/**
 * Minimax P(>= `need` wins) among strategies that never reach a forbidden cell.
 *
 * `null` carries the same meaning as in `solveAvoiding`: the constraint cannot
 * be met against best play. The propagation rule is identical -- we need one
 * way through, they need one way in -- so the two searches agree exactly on
 * *whether* a dodge is possible and disagree only on what it costs.
 *
 * `probs[i][j]` is the probability OUR player `i` beats THEIR player `j`.
 */
export function solveAvoidingChance(
  probs: Matrix,
  state: ProtocolState,
  forbidden: number,
  need: number,
  dist: readonly number[] = [1],
  memo: Map<string, number | null> = new Map(),
): number | null {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const n = probs.length;
  const key = `${ourPool}|${theirPool}|${attacker}|${attackerSide}|${distKey(dist)}`;
  if (memo.has(key)) return memo.get(key) as number | null;

  let result: number | null;

  if (attacker < 0) {
    let best: number | null = null;
    for (const p of bits(ourPool)) {
      const sub = solveAvoidingChance(
        probs,
        { ourPool: ourPool & ~(1 << p), theirPool, attacker: p, attackerSide: "our" },
        forbidden,
        need,
        dist,
        memo,
      );
      if (sub !== null && (best === null || sub > best)) best = sub;
    }
    memo.set(key, best);
    return best;
  }

  const offeringPool = attackerSide === "our" ? theirPool : ourPool;
  const candidates = bits(offeringPool);

  if (candidates.length === 0) {
    result = atLeast(dist, need);
    memo.set(key, result);
    return result;
  }

  if (candidates.length === 1) {
    const other = candidates[0];
    const [ours, theirs] = attackerSide === "our" ? [attacker, other] : [other, attacker];
    result = isForbidden(forbidden, ours, theirs, n)
      ? null
      : atLeast(extendDistribution(dist, probs[ours][theirs]), need);
    memo.set(key, result);
    return result;
  }

  const defenderIsUs = attackerSide === "their";
  let chosen: number | null = null;
  let sawUnmeetable = false;

  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const value = resolveOfferChance(
        probs,
        state,
        [candidates[a], candidates[b]],
        forbidden,
        need,
        dist,
        memo,
      );
      if (value === null) {
        if (!defenderIsUs) sawUnmeetable = true;
        continue;
      }
      if (chosen === null) chosen = value;
      else if (defenderIsUs ? value > chosen : value < chosen) chosen = value;
    }
    if (sawUnmeetable) break;
  }

  result = sawUnmeetable ? null : chosen;
  memo.set(key, result);
  return result;
}

/** Value of one offer, in round-win probability. Mirrors `resolveOfferAvoiding`. */
function resolveOfferChance(
  probs: Matrix,
  state: ProtocolState,
  pair: [number, number],
  forbidden: number,
  need: number,
  dist: readonly number[],
  memo: Map<string, number | null>,
): number | null {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const n = probs.length;
  const attackerIsUs = attackerSide === "our";
  let best: number | null = null;

  for (const picked of pair) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];

    if (isForbidden(forbidden, ours, theirs, n)) {
      if (!attackerIsUs) return null;
      continue;
    }

    const nextOurPool = attackerIsUs ? ourPool : ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheirPool = attackerIsUs
      ? theirPool & ~(1 << picked) & ~(1 << leftover)
      : theirPool;

    const nextDist = extendDistribution(dist, probs[ours][theirs]);
    const exhausted = popcount(nextOurPool) === 0 && popcount(nextTheirPool) === 0;
    const total = exhausted
      ? atLeast(nextDist, need)
      : solveAvoidingChance(
          probs,
          {
            ourPool: nextOurPool,
            theirPool: nextTheirPool,
            attacker: leftover,
            attackerSide: attackerIsUs ? "their" : "our",
          },
          forbidden,
          need,
          nextDist,
          memo,
        );

    if (total === null) {
      if (!attackerIsUs) return null;
      continue;
    }

    if (best === null) best = total;
    else if (attackerIsUs ? total > best : total < best) best = total;
  }

  return best;
}

/**
 * Guaranteed P(win the round) among strategies that refuse every forbidden cell.
 *
 * Pass `forbidden = 0` for the unconstrained baseline. With `ourTeamFirst =
 * false` they open with whichever player is worst for us, matching the
 * convention in `avoidingFloor` so the two are directly comparable.
 */
export function avoidingWinChance(
  probs: Matrix,
  forbidden: number,
  ourTeamFirst = true,
): number | null {
  const n = probs.length;
  const full = (1 << n) - 1;
  const need = winsNeeded(n);

  if (ourTeamFirst) {
    return solveAvoidingChance(
      probs,
      { ourPool: full, theirPool: full, attacker: -1, attackerSide: "our" },
      forbidden,
      need,
    );
  }

  const memo = new Map<string, number | null>();
  let worst: number | null = null;
  for (let p = 0; p < n; p++) {
    const sub = solveAvoidingChance(
      probs,
      {
        ourPool: full,
        theirPool: full & ~(1 << p),
        attacker: p,
        attackerSide: "their" as Side,
      },
      forbidden,
      need,
      [1],
      memo,
    );
    if (sub === null) return null;
    if (worst === null || sub < worst) worst = sub;
  }
  return worst;
}

/**
 * A dodge priced in the currency that decides the round.
 *
 * `price` is a probability difference, so `0.031` means "refusing this costs
 * roughly three rounds in a hundred". It is not a points total and must never
 * be rendered alongside one without a unit.
 */
export interface ChancePrice {
  cell: Cell;
  /** Second cell, when this prices a pair. */
  second?: Cell;
  /** The rating in the cell, carried through for display. */
  rating: number;
  /** Our chance of taking the round with no constraint. */
  base: number;
  /** Our chance among strategies that refuse the cell. */
  avoided: number | null;
  /** `base - avoided`, as a probability. Non-negative. */
  price: number | null;
  /** True when the refusal costs nothing measurable. */
  free: boolean;
}

/** Chance-valued baseline: what we can guarantee with nothing refused. */
export function winChanceFloor(
  matrix: Matrix,
  ratingMin = 1,
  ratingMax = 5,
  ourTeamFirst = true,
): number {
  const probs = probabilityMatrix(matrix, ratingMin, ratingMax);
  return avoidingWinChance(probs, 0, ourTeamFirst) ?? 0;
}

/**
 * The price of refusing each matchup on the board, one at a time, in round-win
 * probability. Cheapest first.
 *
 * This is the chance-valued twin of `dodgeMap`. The two agree on which dodges
 * are POSSIBLE -- the search structure is identical -- and disagree on which
 * are worth arguing about, which is the entire reason it exists.
 */
export function dodgeMapChance(
  matrix: Matrix,
  ratingMin = 1,
  ratingMax = 5,
  ourTeamFirst = true,
): ChancePrice[] {
  const n = matrix.length;
  const probs = probabilityMatrix(matrix, ratingMin, ratingMax);
  const base = avoidingWinChance(probs, 0, ourTeamFirst) ?? 0;
  const out: ChancePrice[] = [];

  for (let ours = 0; ours < n; ours++) {
    for (let theirs = 0; theirs < n; theirs++) {
      const cell: Cell = { ours, theirs };
      const avoided = avoidingWinChance(probs, cellBit(cell, n), ourTeamFirst);
      const price = avoided === null ? null : base - avoided;
      out.push({
        cell,
        rating: matrix[ours][theirs],
        base,
        avoided,
        price,
        free: price !== null && price < 1e-9,
      });
    }
  }

  out.sort((a, b) => {
    if (a.price === null) return b.price === null ? 0 : 1;
    if (b.price === null) return -1;
    return a.price - b.price || a.rating - b.rating;
  });
  return out;
}

/**
 * Can both of these be refused at once, and what does it cost in round-win
 * probability?
 *
 * Avoidance does not compose, so this cannot be recovered by adding two entries
 * of `dodgeMapChance`. `price === null` means one strategy cannot escape both.
 */
export function pricePairChance(
  matrix: Matrix,
  a: Cell,
  b: Cell,
  ratingMin = 1,
  ratingMax = 5,
  ourTeamFirst = true,
): ChancePrice {
  const n = matrix.length;
  const probs = probabilityMatrix(matrix, ratingMin, ratingMax);
  const base = avoidingWinChance(probs, 0, ourTeamFirst) ?? 0;
  const avoided = avoidingWinChance(probs, forbidCells([a, b], n), ourTeamFirst);
  const price = avoided === null ? null : base - avoided;
  return {
    cell: a,
    second: b,
    rating: matrix[a.ours][a.theirs],
    base,
    avoided,
    price,
    free: price !== null && price < 1e-9,
  };
}
