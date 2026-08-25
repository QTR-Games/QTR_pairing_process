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
