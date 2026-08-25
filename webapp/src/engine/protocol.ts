/**
 * Protocol-aware adversarial analysis.
 *
 * `boardAnalysis.ts` bounds the round by minimising over EVERY perfect
 * assignment. That is safe but loose: many of those assignments cannot actually
 * be reached, because WTC pairing is a turn-taking game, not a free choice of
 * permutation.
 *
 * This module plays the real game.
 *
 * ## The protocol
 *
 * One side puts a player forward. The other side offers TWO of theirs. The
 * putting-forward side picks which of the two plays. The player who was offered
 * and not picked is then put forward by their own side, and the roles swap.
 * That repeats until one player remains on each side, who are forced together.
 *
 * Two separate decisions therefore exist at every step, and they belong to
 * DIFFERENT sides:
 *   1. which pair to offer      -- belongs to the defending side
 *   2. which of the pair plays  -- belongs to the attacking side
 *
 * The leftover-becomes-next-attacker rule is what makes a "bus" possible: a
 * side can offer a pair knowing that whichever one is declined gets to dictate
 * the following matchup. It is the mechanic the home team lost to in 2024.
 *
 * ## How the opponent is modelled
 *
 * Finding 12 measured the correlation between two teams' ratings of the same
 * 25 matchups at r = -0.049. The mirror axiom -- that their grid is ours
 * reflected -- is false, so we cannot infer which matchups they WANT.
 *
 * We therefore do not try. The opponent here minimises OUR total on OUR OWN
 * numbers. That is not a claim about their preferences; it is a bound. Whatever
 * they are actually optimising, they cannot do worse to us than the worst they
 * could do to us, so `protocolFloor` is a guarantee that survives not knowing
 * their grid at all.
 *
 * That bound is real, but the paragraph above used to imply it dodged Finding
 * 12. It does not, and the algebra is one line: a side maximising O = 1 - M is
 * maximising sum(1 - M), which is minimising sum(M). "Worst-case opponent" and
 * "mirror axiom" are therefore the SAME opponent wearing different clothes.
 * `measure.opponent.test.ts` asserts this equivalence on all 31 real boards, to
 * nine decimal places, and it runs in CI rather than behind the measurement
 * flag -- if anyone ever makes these two models genuinely differ, it should be
 * a deliberate act with a failing test in front of it.
 *
 * So this is a floor and only a floor. Finding 16 priced it: on real data it
 * understates the realised total by 1.40 points, up to 2.5 on one board. The
 * ranking it produces is nonetheless safe -- following it costs 0.07 points of
 * regret -- so the fix was never to change this solver, but to stop presenting
 * its output as a prediction. `outlook` in ./opponent.ts supplies the
 * complementary "if they play their own board" figure, and the verdict screen
 * now shows both.
 *
 * The result is tighter than the assignment floor and strictly more honest than
 * assuming they cooperate.
 */

import type { Matrix } from "./boardAnalysis";

export interface ProtocolResult {
  /** Round total we can guarantee against a worst-case opponent. */
  value: number;
  /** The decision to take now, when one is ours to make. */
  best?: ProtocolMove;
}

export type ProtocolMove =
  | { kind: "offer"; players: [number, number] }
  | { kind: "pick"; ours: number; theirs: number };

export type Side = "our" | "their";

export interface ProtocolState {
  /** Bitmask of our players still unpaired. */
  ourPool: number;
  /** Bitmask of their players still unpaired. */
  theirPool: number;
  /** Index of the player currently put forward, or -1 at the very start. */
  attacker: number;
  /** Which side the put-forward player belongs to. */
  attackerSide: Side;
}

const bits = (mask: number): number[] => {
  const out: number[] = [];
  for (let i = 0; mask >> i; i++) if (mask & (1 << i)) out.push(i);
  return out;
};

const popcount = (mask: number): number => bits(mask).length;

/**
 * A memo table bound to the board it was filled from.
 *
 * `solveProtocol`'s memo key is `ourPool|theirPool|attacker|attackerSide` and
 * deliberately does NOT include the matrix, because carrying 25 numbers in a
 * string key would cost more than the lookup saves. That makes the memo
 * perfectly reusable across states of the same board, and silently wrong
 * across different boards -- it would hand back another board's answer with no
 * error and no visible symptom.
 *
 * Pairing the map with the matrix it belongs to turns that into a thrown error
 * at the call site. Same reasoning as `pickTieBreak`'s required `ratingSpan`:
 * the only way a caller gets this wrong is silently, so make it loud.
 *
 * Reuse is the point. Because the key covers the whole state, one cache stays
 * valid for an entire round -- every tap narrows the pools, and the subtrees
 * below the new state were already searched while valuing the old one.
 */
export interface SolveCache {
  readonly matrix: Matrix;
  readonly memo: Map<string, ProtocolResult>;
}

/** A cache for one board. Hold it as long as the board does not change. */
export function solveCache(matrix: Matrix): SolveCache {
  return { matrix, memo: new Map<string, ProtocolResult>() };
}

/**
 * The memo to use for `matrix`, or a fresh private one when no cache is given.
 *
 * Reference equality on purpose: two structurally equal matrices are still two
 * different boards as far as a caller is concerned, and a deep compare here
 * would cost more than the memo saves.
 */
export function memoFor(matrix: Matrix, cache?: SolveCache): Map<string, ProtocolResult> {
  if (!cache) return new Map<string, ProtocolResult>();
  if (cache.matrix !== matrix) {
    throw new Error(
      "SolveCache belongs to a different board. Memo keys omit the matrix, so " +
        "reusing one across boards returns the wrong board's answers.",
    );
  }
  return cache.memo;
}

/**
 * Exact minimax value of a pairing state.
 *
 * We maximise; the opponent minimises. Both the offer and the pick are real
 * decisions with real owners, so both are searched.
 *
 * Returns the guaranteed round total, and -- when the immediate decision is
 * ours -- which move achieves it.
 */
export function solveProtocol(
  matrix: Matrix,
  state: ProtocolState,
  memo: Map<string, ProtocolResult> = new Map(),
): ProtocolResult {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const key = `${ourPool}|${theirPool}|${attacker}|${attackerSide}`;
  const cached = memo.get(key);
  if (cached) return cached;

  let result: ProtocolResult;

  if (attacker < 0) {
    // Opening: our side must put a player forward. We choose which.
    let bestValue = -Infinity;
    let bestMove: ProtocolMove | undefined;
    for (const p of bits(ourPool)) {
      const sub = solveProtocol(
        matrix,
        {
          ourPool: ourPool & ~(1 << p),
          theirPool,
          attacker: p,
          attackerSide: "our",
        },
        memo,
      );
      if (sub.value > bestValue) {
        bestValue = sub.value;
        bestMove = { kind: "pick", ours: p, theirs: -1 };
      }
    }
    result = { value: bestValue, best: bestMove };
    memo.set(key, result);
    return result;
  }

  // The side that does NOT own the attacker offers two of its players.
  const offeringPool = attackerSide === "our" ? theirPool : ourPool;
  const candidates = bits(offeringPool);

  if (candidates.length === 0) {
    result = { value: 0 };
    memo.set(key, result);
    return result;
  }

  if (candidates.length === 1) {
    // Forced: the last two players are paired with no decision left.
    const other = candidates[0];
    const [ours, theirs] =
      attackerSide === "our" ? [attacker, other] : [other, attacker];
    result = { value: matrix[ours][theirs] };
    memo.set(key, result);
    return result;
  }

  // Enumerate every pair the defending side could offer.
  const offers: { pair: [number, number]; value: number }[] = [];
  for (let a = 0; a < candidates.length; a++) {
    for (let b = a + 1; b < candidates.length; b++) {
      const pair: [number, number] = [candidates[a], candidates[b]];
      offers.push({ pair, value: resolveOffer(matrix, state, pair, memo) });
    }
  }

  // The offer belongs to the defending side; the pick belongs to the attacker.
  // When our player is forward, THEY offer, so they choose the worst offer for us.
  const defenderIsUs = attackerSide === "their";
  let chosen = offers[0];
  for (const o of offers) {
    if (defenderIsUs ? o.value > chosen.value : o.value < chosen.value) chosen = o;
  }

  result = {
    value: chosen.value,
    best: defenderIsUs ? { kind: "offer", players: chosen.pair } : undefined,
  };
  memo.set(key, result);
  return result;
}

/**
 * Value of a specific offer, once the attacking side picks from it.
 *
 * The picked player is paired with the attacker and banks their rating. The
 * player who was offered and declined becomes the next attacker for their own
 * side -- the rule that lets a side steer the following matchup.
 */
function resolveOffer(
  matrix: Matrix,
  state: ProtocolState,
  pair: [number, number],
  memo: Map<string, ProtocolResult>,
): number {
  const { ourPool, theirPool, attacker, attackerSide } = state;
  const attackerIsUs = attackerSide === "our";
  let best = attackerIsUs ? -Infinity : Infinity;

  for (const picked of pair) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [attacker, picked] : [picked, attacker];
    const banked = matrix[ours][theirs];

    const nextOurPool = attackerIsUs ? ourPool : ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheirPool = attackerIsUs
      ? theirPool & ~(1 << picked) & ~(1 << leftover)
      : theirPool;

    const exhausted = popcount(nextOurPool) === 0 && popcount(nextTheirPool) === 0;
    const rest = exhausted
      ? 0
      : solveProtocol(
          matrix,
          {
            ourPool: nextOurPool,
            theirPool: nextTheirPool,
            attacker: leftover,
            attackerSide: attackerIsUs ? "their" : "our",
          },
          memo,
        ).value;

    const total = banked + rest;
    // The attacking side picks. We maximise our total; they minimise it.
    if (attackerIsUs ? total > best : total < best) best = total;
  }
  return best;
}

/**
 * The round total we can guarantee under the real pairing protocol.
 *
 * `ourTeamFirst` selects who puts a player forward at the start. This is the
 * number to trust when deciding whether a round is safe: unlike the assignment
 * floor it only counts outcomes the protocol can actually produce, and unlike
 * the current engine it does not assume the opponent cooperates.
 */
export function protocolFloor(matrix: Matrix, ourTeamFirst = true): ProtocolResult {
  const n = matrix.length;
  const full = (1 << n) - 1;
  if (ourTeamFirst) {
    return solveProtocol(matrix, {
      ourPool: full,
      theirPool: full,
      attacker: -1,
      attackerSide: "our",
    });
  }
  // They open: they put a player forward and choose the one worst for us.
  const memo = new Map<string, ProtocolResult>();
  let worst = Infinity;
  for (let p = 0; p < n; p++) {
    const sub = solveProtocol(
      matrix,
      {
        ourPool: full,
        theirPool: full & ~(1 << p),
        attacker: p,
        attackerSide: "their",
      },
      memo,
    );
    if (sub.value < worst) worst = sub.value;
  }
  return { value: worst };
}

/**
 * How much optimism the assignment floor carries.
 *
 * A positive gap means the protocol can force us below the naive assignment
 * bound is able to express, i.e. the turn-taking structure itself costs us
 * points that a permutation-only view cannot see.
 */
export function protocolGap(
  matrix: Matrix,
  assignmentFloorValue: number,
  ourTeamFirst = true,
): number {
  return protocolFloor(matrix, ourTeamFirst).value - assignmentFloorValue;
}

/**
 * Step 1 of the pairing protocol: which side to take when you win the dice-off.
 *
 * Player Pack 2026 v1.1 p.20 step 1, verbatim: "Dice off until one captain has
 * rolled higher than the other. The captain with the higher roll gets to choose
 * whether they are Team A, or Team B in the process below." Team B puts the
 * first player up, which is `ourTeamFirst = true` here.
 *
 * The app has always let you set this by hand. It has never told you which one
 * to pick, and it is the single decision in a round that costs nothing to get
 * right and cannot be recovered once made.
 *
 * ## What the answer turns out to be
 *
 * Measured over all 31 real WTC boards (`measure.openOrReceive.test.ts`),
 * making them open is better on 18 and identical on 13. Better on ZERO. Worth a
 * mean 0.58 points, up to a full point; in P(>= 3 wins), a mean 4.63% and up to
 * 7.97%. Points and probability pick the same side on 31 of 31.
 *
 * ## Why it is a default and not a law
 *
 * A hunt over 16,000 random 5v5 boards (`measure.openTheorem.test.ts`) found
 * boards where opening wins, on real scales:
 *
 *     1-5    opening better on  0 / 5,000
 *     1-10   opening better on  2 / 5,000   (max 1.00 pt)
 *     1-2    opening better on 11 / 3,000   (max 1.00 pt)
 *     4-5    opening better on  9 / 3,000   (max 1.00 pt)
 *
 * Only 5v5 is searched. The one other format is 3v3, and 3v3 uses a different
 * pairing process entirely -- not this protocol -- so a 3x3 board would
 * measure nothing about anything. Board sizes that are not formats are not
 * searched at all.
 *
 * The pattern is that exceptions live where ratings tie. On a compressed scale
 * (1-2, 4-5) a third of boards are dead level and roughly 1 in 300 flips; on a
 * wide 1-10 scale almost nothing ties and it is 1 in 2,500. That matters,
 * because a team who rate everything a 4 or a 5 are exactly the team most
 * likely to hit one.
 *
 * So the function computes the answer rather than printing "always receive".
 * The default is right on well over 99% of boards, but the exceptions cost a
 * full point, they exist on the scale being used at the event, and computing
 * them costs one extra call.
 *
 * Both numbers are floors, so the comparison survives not knowing their grid:
 * whatever they are optimising, they cannot take us below either figure.
 *
 * ## What this function does NOT price
 *
 * Opening is not only a matchup concession. It also buys table control. Player
 * Pack 2026 v1.1 p.20 step 8: "The team that doesn't pick the match-up chooses
 * the table each time." Step 10 spells the trade out: team B "gets to choose
 * two match-ups and three tables, while team A will get to choose three
 * match-ups and two table". Working it through matchup by matchup:
 *
 *     matchup   pairing   table     tables left
 *     1         B         A         5
 *     2         A         B         4
 *     3         B         A         3
 *     4         A         B         2
 *     5         A         B         1  <- forced, not a choice
 *
 * So opening trades one matchup pick for one extra table pick, and the pack
 * oversells even that: B's third table is the last one standing. Real picks are
 * two apiece.
 *
 * This function prices the matchup half only. The unpriced half favours
 * opening, which is the direction that could in principle flip the answer.
 *
 * Two independent things say it does not. The 31-board measurement above puts
 * receiving ahead on 18 and level on 13, never behind; and the player community
 * has settled on receiving as the better side. A table edge large enough to
 * overturn a result that one-sided would have shown up in how the game is
 * actually played.
 *
 * The table half is deliberately left unpriced, and that is a scoping decision
 * rather than a gap waiting to be filled. Terrain is pre-set by the organisers;
 * nobody places it, nobody designs a list for a specific table, and the whole
 * decision is "which of these five suits what my army does". That is a judgement
 * a player makes standing in front of the tables, and putting a number on it
 * would dress up a read as a calculation. What the app can honestly do is say
 * WHO holds each pick -- the column above, derived from the rules alone, with no
 * data entry -- and leave the choice itself to the person making it.
 */
export interface OpeningChoice {
  /** True when we should put the first player up. */
  weOpen: boolean;
  /** Guaranteed total if we open. */
  openValue: number;
  /** Guaranteed total if they open. */
  receiveValue: number;
  /** Points given up by taking the wrong side. Zero when it makes no odds. */
  gain: number;
}

export function openingChoice(matrix: Matrix): OpeningChoice {
  const openValue = protocolFloor(matrix, true).value;
  const receiveValue = protocolFloor(matrix, false).value;
  return {
    weOpen: openValue > receiveValue,
    openValue,
    receiveValue,
    gain: Math.abs(openValue - receiveValue),
  };
}
