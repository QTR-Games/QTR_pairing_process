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

/**
 * A stored fraction (0 at the worst matchup, 1 at the best) straight to a win
 * probability, without routing through a scale.
 *
 * `(rating - mid) / span` in {@link toWinProbability} is exactly `fraction -
 * 0.5`, so this is the same line expressed in the unit a board is actually
 * stored in (`model/scale.ts`). Using it keeps a displayed percentage
 * scale-independent -- a board entered on 1-5 and re-read on 1-20 shows the
 * same number -- and matches `ratingColor`, which is also driven straight off
 * the fraction rather than the snapped scale value.
 */
export function winProbabilityFromFraction(fraction: number): number {
  const p = 0.5 + SPREAD * (fraction - 0.5);
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
 * Signature of a win distribution, for use in a memo key.
 *
 * P(>= k) does not accumulate, so any search over pairings that values itself
 * in round-win chance has to carry the distribution of wins so far and key its
 * memo on it. That makes this function the hot path of every such search, and
 * it is genuinely hot: writing it with `toFixed(9)` -- the obvious way -- took
 * the 24-trial chance outlook from 161 ms to 338 ms per board, measured over
 * the 31 saved boards. Integer rounding at the same nine places carries exactly
 * the same information and keeps the number formatting out of the inner loop.
 */
export function distributionKey(dist: readonly number[]): string {
  let out = "";
  for (let i = 0; i < dist.length; i++) out += (i ? "," : "") + Math.round(dist[i] * 1e9);
  return out;
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

/**
 * Worst and best round-win chance over every perfect assignment of a board.
 *
 * The probability-valued twin of `assignmentExtremes`, and it has to be a
 * different algorithm rather than the same one with different numbers.
 * `assignmentExtremes` is a Hungarian solve, which works because a points total
 * is a SUM over the assignment: fixing one pair leaves the value of the rest
 * unchanged. P(>= 3 of 5) is not a sum, so there is no cost matrix to hand to
 * an assignment solver, for the same reason `solveAvoidingChance` cannot
 * memoise on pools alone.
 *
 * So it enumerates. That is affordable precisely because a round is five games:
 * the recursion visits 326 nodes on a 5x5 and the whole call is 0.24 ms
 * measured, against 16.7 ms for one `winChanceFloor` solve on the same board.
 * It is the cheapest number on the panel, not the dearest.
 *
 * Returns `[floor, ceiling]`: the chance if the pairings fall as badly as they
 * possibly can, and the chance if they fall as well as they possibly can.
 * Neither is a prediction -- the floor ignores that half the pairing decisions
 * are ours, and the ceiling ignores that the opponent gets a say -- they bound
 * what is still reachable.
 */
export function assignmentChanceExtremes(
  probs: readonly (readonly number[])[],
): [number, number] {
  const n = probs.length;
  if (n === 0) return [0, 0];
  const need = winsNeeded(n);

  let lo = Infinity;
  let hi = -Infinity;
  const used = new Array<boolean>(probs[0].length).fill(false);

  const walk = (ours: number, dist: readonly number[]): void => {
    if (ours === n) {
      const v = atLeast(dist, need);
      if (v < lo) lo = v;
      if (v > hi) hi = v;
      return;
    }
    for (let theirs = 0; theirs < used.length; theirs++) {
      if (used[theirs]) continue;
      used[theirs] = true;
      walk(ours + 1, extendDistribution(dist, probs[ours][theirs]));
      used[theirs] = false;
    }
  };

  walk(0, [1]);
  return [lo, hi];
}
