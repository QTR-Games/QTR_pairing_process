/**
 * What actually happens, as opposed to the worst that could.
 *
 * `protocol.ts` returns the value we can guarantee. Finding 16 proved that this
 * number, despite being described as an assumption-free bound, is produced by an
 * opponent who is exactly our mirror -- because a side maximising `1 - M` is a
 * side minimising `M`. Finding 12 measured two real teams' grids at r = -0.049,
 * so that opponent does not exist.
 *
 * The consequence is not that the floor is wrong. It is a true floor, and the
 * ranking built on it costs only 0.07 points (Finding 16). The consequence is
 * that it is **1.40 points pessimistic** as a description of what will happen,
 * and it has always been displayed without saying so.
 *
 * This module supplies the other number: what we score against an opponent who
 * optimises a board we cannot see.
 *
 * ## The model, stated plainly
 *
 * Their grid is drawn independently of ours from the distribution of real
 * ratings. That is the only structure Finding 12 supports -- near-zero
 * correlation, same marginal. We then play the real protocol as a general-sum
 * game: we maximise our grid, they maximise theirs. Neither side is minimising
 * the other, which is the whole point.
 *
 * This is a model, not a prophecy, and the UI must label it as one. The floor is
 * rigorous; this is grounded. They answer different questions:
 *
 *   floor     what if they hunt me perfectly   -- must not lose
 *   expected  what if they just play their own board -- must win
 *
 * ## Determinism
 *
 * The sampling is seeded from the board itself, so the same board always yields
 * the same number. A figure that flickered between renders would be unusable at
 * a table, where the first thing you do with a surprising number is look again.
 */

import type { Matrix } from "./boardAnalysis";
import type { Side } from "./protocol";
import {
  atLeast,
  distributionKey,
  extendDistribution,
  probabilityMatrix,
  winsNeeded,
} from "./winProbability";

/** Enough to converge: the estimate is stable to ±0.02 pts by 10 trials. */
const DEFAULT_TRIALS = 24;

const bits = (mask: number): number[] => {
  const out: number[] = [];
  for (let i = 0; mask >> i; i++) if (mask & (1 << i)) out.push(i);
  return out;
};

const popcount = (mask: number): number => bits(mask).length;

interface Grids {
  ours: Matrix;
  theirs: Matrix;
}

interface JointValue {
  us: number;
  them: number;
}

export interface JointState {
  ourPool: number;
  theirPool: number;
  attacker: number;
  attackerSide: Side;
}

const own = (v: JointValue, side: Side): number => (side === "our" ? v.us : v.them);

/**
 * Exact general-sum value of a pairing state under two different grids.
 *
 * Identical in structure to `solveProtocol`, with one difference that matters:
 * every decision is resolved in favour of the side that OWNS it, judged on that
 * side's own numbers. Give both sides the same grid and this reduces to
 * cooperation; give them mirrored grids and it reduces exactly to minimax
 * (asserted in `measure.opponent.test.ts`).
 */
export function solveJoint(
  g: Grids,
  state: JointState,
  memo: Map<string, JointValue>,
): JointValue {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const key = `${ourPool}|${theirPool}|${attacker}|${attackerSide}`;
  const cached = memo.get(key);
  if (cached) return cached;

  let result: JointValue;

  if (attacker < 0) {
    const opener = attackerSide;
    const pool = opener === "our" ? ourPool : theirPool;
    let best: JointValue | undefined;
    for (const p of bits(pool)) {
      const sub = solveJoint(
        g,
        {
          ourPool: opener === "our" ? ourPool & ~(1 << p) : ourPool,
          theirPool: opener === "their" ? theirPool & ~(1 << p) : theirPool,
          attacker: p,
          attackerSide: opener,
        },
        memo,
      );
      if (!best || own(sub, opener) > own(best, opener)) best = sub;
    }
    result = best ?? { us: 0, them: 0 };
    memo.set(key, result);
    return result;
  }

  const offeringSide: Side = attackerSide === "our" ? "their" : "our";
  const offeringPool = offeringSide === "our" ? ourPool : theirPool;
  const candidates = bits(offeringPool);

  if (candidates.length === 0) {
    result = { us: 0, them: 0 };
    memo.set(key, result);
    return result;
  }

  if (candidates.length === 1) {
    const other = candidates[0];
    const [ours, theirs] =
      attackerSide === "our" ? [attacker, other] : [other, attacker];
    result = { us: g.ours[ours][theirs], them: g.theirs[ours][theirs] };
    memo.set(key, result);
    return result;
  }

  let best: JointValue | undefined;
  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const v = resolveOfferJoint(g, state, [candidates[a], candidates[b]], memo);
      if (!best || own(v, offeringSide) > own(best, offeringSide)) best = v;
    }
  }

  result = best ?? { us: 0, them: 0 };
  memo.set(key, result);
  return result;
}

function resolveOfferJoint(
  g: Grids,
  state: JointState,
  pair: [number, number],
  memo: Map<string, JointValue>,
): JointValue {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const attackerIsUs = attackerSide === "our";
  let best: JointValue | undefined;

  for (const picked of pair) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];

    const nextOurPool = attackerIsUs
      ? ourPool
      : ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheirPool = attackerIsUs
      ? theirPool & ~(1 << picked) & ~(1 << leftover)
      : theirPool;

    const exhausted = popcount(nextOurPool) === 0 && popcount(nextTheirPool) === 0;
    const rest = exhausted
      ? { us: 0, them: 0 }
      : solveJoint(
          g,
          {
            ourPool: nextOurPool,
            theirPool: nextTheirPool,
            attacker: leftover,
            attackerSide: attackerIsUs ? "their" : "our",
          },
          memo,
        );

    const total: JointValue = {
      us: g.ours[ours][theirs] + rest.us,
      them: g.theirs[ours][theirs] + rest.them,
    };

    if (!best || own(total, attackerSide) > own(best, attackerSide)) best = total;
  }

  return best ?? { us: 0, them: 0 };
}

/**
 * The same general-sum solve, valued in the chance of taking the round.
 *
 * `solveJoint` above adds ratings up, which is what lets it memoise on the
 * pools alone: a total does not care how the wins are distributed. P(>= 3 of 5)
 * does, so this carries each side's distribution of wins so far and evaluates
 * only at a complete assignment -- the same structure, and for the same reason,
 * as `solveAvoidingChance`.
 *
 * Both distributions have to be carried, not one. Their grid is sampled
 * independently of ours, so their chance of winning a game is not one minus
 * ours; that independence is the whole premise of this module. Each side
 * maximises its own P(>= 3) and neither is minimising the other.
 *
 * The cheap alternative -- solve in points as before, then convert the
 * resulting assignment to probabilities -- was rejected rather than
 * overlooked. It optimises the wrong thing, and the way it is wrong is exactly
 * the failure `winProbability.ts` was written to fix: a points solve is
 * indifferent between a 9 and a 1 and two 5s, so it will happily hand back the
 * assignment that reads better as a total and worse as a round.
 */
export function solveJointChance(
  g: Grids,
  state: JointState,
  need: number,
  ourDist: readonly number[],
  theirDist: readonly number[],
  memo: Map<string, JointValue>,
): JointValue {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const key =
    `${ourPool}|${theirPool}|${attacker}|${attackerSide}|` +
    `${distributionKey(ourDist)}|${distributionKey(theirDist)}`;
  const cached = memo.get(key);
  if (cached) return cached;

  let result: JointValue;

  if (attacker < 0) {
    const opener = attackerSide;
    const pool = opener === "our" ? ourPool : theirPool;
    let best: JointValue | undefined;
    for (const p of bits(pool)) {
      const sub = solveJointChance(
        g,
        {
          ourPool: opener === "our" ? ourPool & ~(1 << p) : ourPool,
          theirPool: opener === "their" ? theirPool & ~(1 << p) : theirPool,
          attacker: p,
          attackerSide: opener,
        },
        need,
        ourDist,
        theirDist,
        memo,
      );
      if (!best || own(sub, opener) > own(best, opener)) best = sub;
    }
    result = best ?? { us: 0, them: 0 };
    memo.set(key, result);
    return result;
  }

  const offeringSide: Side = attackerSide === "our" ? "their" : "our";
  const offeringPool = offeringSide === "our" ? ourPool : theirPool;
  const candidates = bits(offeringPool);

  if (candidates.length === 0) {
    result = { us: atLeast(ourDist, need), them: atLeast(theirDist, need) };
    memo.set(key, result);
    return result;
  }

  if (candidates.length === 1) {
    const other = candidates[0];
    const [ours, theirs] =
      attackerSide === "our" ? [attacker, other] : [other, attacker];
    result = {
      us: atLeast(extendDistribution(ourDist, g.ours[ours][theirs]), need),
      them: atLeast(extendDistribution(theirDist, g.theirs[ours][theirs]), need),
    };
    memo.set(key, result);
    return result;
  }

  let best: JointValue | undefined;
  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const v = resolveOfferChance(
        g,
        state,
        [candidates[a], candidates[b]],
        need,
        ourDist,
        theirDist,
        memo,
      );
      if (!best || own(v, offeringSide) > own(best, offeringSide)) best = v;
    }
  }

  result = best ?? { us: 0, them: 0 };
  memo.set(key, result);
  return result;
}

/** Value of one offer, in round-win chance. Mirrors `resolveOfferJoint`. */
function resolveOfferChance(
  g: Grids,
  state: JointState,
  pair: [number, number],
  need: number,
  ourDist: readonly number[],
  theirDist: readonly number[],
  memo: Map<string, JointValue>,
): JointValue {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const attackerIsUs = attackerSide === "our";
  let best: JointValue | undefined;

  for (const picked of pair) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];

    const nextOurPool = attackerIsUs
      ? ourPool
      : ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheirPool = attackerIsUs
      ? theirPool & ~(1 << picked) & ~(1 << leftover)
      : theirPool;

    const nextOurDist = extendDistribution(ourDist, g.ours[ours][theirs]);
    const nextTheirDist = extendDistribution(theirDist, g.theirs[ours][theirs]);

    const exhausted = popcount(nextOurPool) === 0 && popcount(nextTheirPool) === 0;
    const total: JointValue = exhausted
      ? { us: atLeast(nextOurDist, need), them: atLeast(nextTheirDist, need) }
      : solveJointChance(
          g,
          {
            ourPool: nextOurPool,
            theirPool: nextTheirPool,
            attacker: leftover,
            attackerSide: attackerIsUs ? "their" : "our",
          },
          need,
          nextOurDist,
          nextTheirDist,
          memo,
        );

    if (!best || own(total, attackerSide) > own(best, attackerSide)) best = total;
  }

  return best ?? { us: 0, them: 0 };
}

/** Seeded from the board so the displayed figure never moves on its own. */
function seedFrom(matrix: Matrix): number {
  let h = 2166136261;
  for (const row of matrix) {
    for (const v of row) {
      h ^= Math.round(v * 1000);
      h = Math.imul(h, 16777619);
    }
  }
  return h >>> 0;
}

function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export interface Outlook {
  /** Worst case: they hunt us perfectly. Rigorous, no model assumptions. */
  floor: number;
  /** Typical case against an opponent optimising their own board. */
  expected: number;
  /** Bad tail of that distribution -- roughly, the "bussed" outcome. */
  low: number;
  /** Good tail: what a gamble is worth when it comes off. */
  high: number;
  /**
   * Standard error of `expected`, in whatever units `expected` carries.
   *
   * `expected` is a Monte Carlo mean over `trials` sampled opponent boards, so
   * it carries sampling error whether or not anyone looks at it. Measured
   * against a 4000-trial reference on the 31 real boards, the shipped 24-trial
   * estimate lands 0.053 pts from the truth on average and 0.218 pts away at
   * worst.
   *
   * That is small enough to trust for reading -- no decision turns on a
   * twentieth of a point -- but callers that COMPARE `expected` to something
   * are a different case. Verdict.tsx picks between two opposite
   * recommendations on `expected > tau`, and 5 of the 31 real boards sit closer
   * to that line than the error, with one exactly on it. On those boards the
   * advice was being chosen by the random draw.
   *
   * Raising the trial count is the expensive answer: 192 trials cuts the error
   * roughly in half and costs eight times the time, on the phone, which is the
   * device that actually goes to the event. Reporting the uncertainty costs a
   * pass over an array we have already built. So the estimate carries its own
   * error bar and comparisons can decline to answer when the gap is inside it.
   */
  stderr: number;
}

/**
 * Floor, typical and upside for a state, in round points.
 *
 * `floorValue` is passed in rather than recomputed so the caller keeps a single
 * source of truth for the guaranteed number and the two cannot drift apart.
 */
export function outlook(
  matrix: Matrix,
  state: JointState,
  floorValue: number,
  trials: number = DEFAULT_TRIALS,
): Outlook {
  return summarise(
    sampleOpponentBoards(matrix, state, trials).map(
      (theirs) => solveJoint({ ours: matrix, theirs }, state, new Map()).us,
    ),
    floorValue,
  );
}

/**
 * The same read, in the chance of actually taking the round.
 *
 * Deliberately the same sampled opponents as `outlook`: the seed depends only
 * on the board and the state, so a screen showing both currencies is showing
 * two readings of one set of two dozen opponents rather than two unrelated
 * draws that happen to sit next to each other.
 *
 * ## Cost, because it is not free
 *
 * Measured over the 31 saved boards on a desktop: 161 ms per board at 24
 * trials, 187 ms at worst, against 33 ms for the points version. It is now the
 * most expensive thing the verdict panel does, ahead of the single
 * `winChanceFloor` solve at 17 ms.
 *
 * That is the price of solving in the currency that decides the round rather
 * than converting a points answer afterwards, and it buys a real difference:
 * see the note on `solveJointChance`. It is paid on a board tab that also runs
 * the points outlook, a protocol floor for each side and a reach report, so it
 * is a large share of a small total rather than a new order of magnitude.
 */
export function chanceOutlook(
  matrix: Matrix,
  state: JointState,
  floorValue: number,
  ratingMin = 1,
  ratingMax = 5,
  trials: number = DEFAULT_TRIALS,
): Outlook {
  const ours = probabilityMatrix(matrix, ratingMin, ratingMax);
  const need = winsNeeded(matrix.length);

  return summarise(
    sampleOpponentBoards(matrix, state, trials).map(
      (theirs) =>
        solveJointChance(
          { ours, theirs: probabilityMatrix(theirs, ratingMin, ratingMax) },
          state,
          need,
          [1],
          [1],
          new Map(),
        ).us,
    ),
    floorValue,
  );
}

/**
 * The opponent boards both readings are scored against.
 *
 * Their grid is drawn cell by cell from the pool of ratings on our own board,
 * which is the only structure Finding 12 supports: near-zero correlation, same
 * marginal.
 */
function sampleOpponentBoards(matrix: Matrix, state: JointState, trials: number): Matrix[] {
  const n = matrix.length;
  const pool: number[] = [];
  for (const row of matrix) for (const v of row) pool.push(v);

  const rand = rng(seedFrom(matrix) ^ (state.ourPool * 31 + state.theirPool));

  return Array.from({ length: trials }, () =>
    Array.from({ length: n }, () =>
      Array.from({ length: n }, () => pool[Math.floor(rand() * pool.length)]),
    ),
  );
}

/** Mean, tails and error bar of a set of trial results, in their own units. */
function summarise(values: number[], floorValue: number): Outlook {
  const totals = [...values].sort((a, b) => a - b);
  const mean = totals.reduce((a, b) => a + b, 0) / totals.length;
  const at = (q: number): number => totals[Math.min(totals.length - 1, Math.floor(q * totals.length))];

  // Sample standard error of the mean. Bessel-corrected, and guarded for the
  // degenerate single-trial case a caller could ask for.
  const variance =
    totals.length > 1
      ? totals.reduce((a, b) => a + (b - mean) ** 2, 0) / (totals.length - 1)
      : 0;
  const stderr = Math.sqrt(variance / totals.length);

  // A discrete, left-skewed sample can put the 10th percentile ABOVE the mean:
  // if a couple of trials end in disaster they drag the average below p10 while
  // 90% of outcomes sit higher. That is a true description of the distribution
  // and a nonsensical thing to print -- "low 15, typical 14.9" reads as a bug.
  // Clamp so the triple is always ordered on screen; the disaster itself is
  // still represented, by `floor`.
  return {
    floor: floorValue,
    expected: mean,
    low: Math.min(at(0.1), mean),
    high: Math.max(at(0.9), mean),
    stderr,
  };
}
