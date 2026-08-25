/**
 * Ratings as probabilities, and the chance of actually taking the round.
 *
 * ## Why this module exists
 *
 * Everything else in this engine counts POINTS. `protocolFloor` guarantees a
 * total, `dodgeMap` prices a refusal in rating units, and the verdict compares
 * a total against `evenThreshold`. That is a coherent currency and it is the
 * wrong one for a decision.
 *
 * A round is won by winning three of five games. Points are a proxy for that
 * and a poor one near the margin, because the sum is indifferent to how the
 * wins are distributed. Trading a 9 and a 1 for two 5s leaves the total
 * unchanged and moves the chance of taking the round a long way. The engine
 * cannot currently see that difference, which is why `dodgeMap` reports a
 * price of 0.000 on every fixture board: in points, it genuinely costs nothing
 * to choose which bad cell you eat.
 *
 * ## The mapping, and what it is not
 *
 * A rating is turned into a win probability by a straight line through the
 * middle of the scale:
 *
 *     p = 0.5 + SPREAD * (rating - midpoint) / span
 *
 * clamped away from certainty. On a 1-5 board a 1 reads as ~8% and a 5 as
 * ~92%; on 1-10 a 1 and a 10 read identically, because the formula is defined
 * in terms of the scale's own midpoint and span. That scale-independence is
 * deliberate and matches `evenThreshold`.
 *
 * `SPREAD = 0.85` is not measured from results. It is an anchoring choice --
 * "a 1 is about 8%, a 5 is about 92%" -- and it is the single largest
 * unverified assumption in this file. It is exported so it can be swept, and
 * every consumer should treat the resulting percentages as an ORDERING over
 * options rather than a forecast. The claim this module supports is "dodging
 * this cell costs more than dodging that one", not "you will win 63.4% of the
 * time".
 *
 * Deliberately mirrors the Python probes character for character
 * (`files/probe_dodge_price.py`, `probe_lexicographic.py`) so a number
 * discovered on the desktop reproduces on the phone.
 */

/** Clamp distance from 0 and 1. No matchup in this game is a certainty. */
export const EPS = 0.02;

/**
 * Slope of the rating-to-probability line, as a fraction of a half-scale.
 *
 * At 0.85 the extremes of the scale sit at 7.5% and 92.5%. Lower values flatten
 * every board toward a coin flip and compress the differences this module
 * exists to expose; higher values push the extremes toward certainty.
 */
export const SPREAD = 0.85;

/**
 * One rating, as the probability that our player wins that game.
 *
 * Scale-independent: `(1, 1, 5)` and `(1, 1, 10)` both return ~0.075, because
 * the argument is the rating's position within its own scale rather than its
 * face value.
 */
export function toWinProbability(rating: number, ratingMin = 1, ratingMax = 5): number {
  const mid = (ratingMin + ratingMax) / 2;
  const span = ratingMax - ratingMin || 1;
  const p = 0.5 + (SPREAD * (rating - mid)) / span;
  return Math.min(1 - EPS, Math.max(EPS, p));
}

/** A whole board of ratings, as win probabilities. */
export function probabilityMatrix(
  matrix: readonly (readonly number[])[],
  ratingMin = 1,
  ratingMax = 5,
): number[][] {
  return matrix.map((row) => row.map((r) => toWinProbability(r, ratingMin, ratingMax)));
}

/**
 * Wins required to take the round: a strict majority of the games.
 *
 * 3 of 5, 2 of 3, 4 of 7. An even game count has no majority at the halfway
 * mark, so `floor(n/2) + 1` is the honest reading of "more than half".
 */
export const winsNeeded = (games: number): number => Math.floor(games / 2) + 1;

/**
 * Distribution of the number of wins across independent games.
 *
 * Returns `dist` where `dist[w]` is the probability of exactly `w` wins. This
 * is the Poisson binomial, computed by convolution because the games have
 * different success probabilities and so the binomial formula does not apply.
 */
export function winDistribution(probs: readonly number[]): number[] {
  let dist = [1];
  for (const p of probs) dist = extendDistribution(dist, p);
  return dist;
}

/**
 * Fold one more game into an existing win distribution.
 *
 * The hot path of the probability-valued protocol search, which folds games in
 * one at a time as the tree assigns them.
 */
export function extendDistribution(dist: readonly number[], p: number): number[] {
  const out = new Array<number>(dist.length + 1).fill(0);
  const q = 1 - p;
  for (let w = 0; w < dist.length; w++) {
    const d = dist[w];
    if (d === 0) continue;
    out[w] += d * q;
    out[w + 1] += d * p;
  }
  return out;
}

/** Probability of at least `k` wins, given a distribution over win counts. */
export function atLeast(dist: readonly number[], k: number): number {
  let total = 0;
  for (let w = Math.max(0, k); w < dist.length; w++) total += dist[w];
  return total;
}

/**
 * Probability of taking the round outright, given each game's win chance.
 *
 * The decision currency of this app, and the thing a captain is actually
 * trying to maximise when they argue about a pairing.
 */
export function roundWinChance(probs: readonly number[]): number {
  return atLeast(winDistribution(probs), winsNeeded(probs.length));
}
