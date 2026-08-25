/**
 * Live pairing advice.
 *
 * `protocol.ts` returns one number: what the round is worth under perfect play.
 * That is the right number to trust, but it is not advice. Standing at a table
 * mid-round you need to know which decision is yours, what your options are,
 * and what each one costs you.
 *
 * This module turns the solver into that.
 *
 * It also answers the question the desktop app has never been able to:
 *
 *   "If I hold this player back, does a better opportunity show up for them
 *    later, or am I leaving points on the table?"
 *
 * That is `playerLeverage`. For each of our players it separates the best total
 * reachable when they are committed NOW from the best total reachable when they
 * are held. The difference is the value of waiting, per player, in points.
 * A ranking cannot express that; only search over the remaining game can.
 */

import type { Matrix } from "./boardAnalysis";
import { outlook } from "./opponent";
import type { ProtocolResult, ProtocolState, Side } from "./protocol";
import { solveProtocol } from "./protocol";

const bits = (mask: number): number[] => {
  const out: number[] = [];
  for (let i = 0; mask >> i; i++) if (mask & (1 << i)) out.push(i);
  return out;
};

/** Who the app should be prompting right now. */
export type Decision =
  | { kind: "open"; owner: Side }
  | { kind: "offer"; owner: Side; attacker: number; attackerSide: Side }
  | { kind: "pick"; owner: Side; attacker: number; attackerSide: Side; pair: [number, number] }
  | { kind: "forced"; ours: number; theirs: number }
  | { kind: "done" };

/** A move we could make, and what it is worth. */
export interface MoveOption {
  /** Our player index this option puts forward or pairs, when meaningful. */
  ours?: number;
  /** Their player index, when meaningful. */
  theirs?: number;
  /** For an offer, the two players being offered. */
  pair?: [number, number];
  /** Guaranteed final round total if this move is taken and play is perfect. */
  value: number;
  /** Points given up versus the best available move. Zero for the best. */
  regret: number;
}

/** The live state of a round in progress. */
export interface LiveState {
  ourPool: number;
  theirPool: number;
  attacker: number;
  attackerSide: Side;
  /** Points already banked by pairings that are locked in. */
  banked: number;
  /** Locked pairings, in the order they were made. */
  committed: { ours: number; theirs: number; value: number }[];
}

export function newRound(n: number, ourTeamFirst: boolean): LiveState {
  const full = (1 << n) - 1;
  return {
    ourPool: full,
    theirPool: full,
    attacker: -1,
    attackerSide: ourTeamFirst ? "our" : "their",
    banked: 0,
    committed: [],
  };
}

/** What decision is on the table, and whose it is. */
export function currentDecision(s: LiveState): Decision {
  const ours = bits(s.ourPool);
  const theirs = bits(s.theirPool);

  if (s.attacker < 0) {
    if (ours.length === 0 && theirs.length === 0) return { kind: "done" };
    return { kind: "open", owner: s.attackerSide };
  }

  const offeringSide: Side = s.attackerSide === "our" ? "their" : "our";
  const offeringPool = offeringSide === "our" ? ours : theirs;

  if (offeringPool.length === 0) return { kind: "done" };
  if (offeringPool.length === 1) {
    const other = offeringPool[0];
    return s.attackerSide === "our"
      ? { kind: "forced", ours: s.attacker, theirs: other }
      : { kind: "forced", ours: other, theirs: s.attacker };
  }
  return {
    kind: "offer",
    owner: offeringSide,
    attacker: s.attacker,
    attackerSide: s.attackerSide,
  };
}

/**
 * Every move available at this state, valued by the solver and ranked.
 *
 * Values are final round totals, so they already include everything banked.
 * That means the numbers on screen are directly comparable to the threshold,
 * with no mental arithmetic at the table.
 */
export function moveOptions(matrix: Matrix, s: LiveState): MoveOption[] {
  const memo = new Map<string, ProtocolResult>();
  const raw: MoveOption[] = [];
  const decision = currentDecision(s);

  if (decision.kind === "open") {
    const pool = decision.owner === "our" ? bits(s.ourPool) : bits(s.theirPool);
    for (const p of pool) {
      const next: ProtocolState = {
        ourPool: decision.owner === "our" ? s.ourPool & ~(1 << p) : s.ourPool,
        theirPool: decision.owner === "their" ? s.theirPool & ~(1 << p) : s.theirPool,
        attacker: p,
        attackerSide: decision.owner,
      };
      const v = solveProtocol(matrix, next, memo).value;
      raw.push(
        decision.owner === "our"
          ? { ours: p, value: s.banked + v, regret: 0 }
          : { theirs: p, value: s.banked + v, regret: 0 },
      );
    }
  } else if (decision.kind === "offer") {
    const pool = decision.owner === "our" ? bits(s.ourPool) : bits(s.theirPool);
    for (let a = 0; a < pool.length; a++) {
      for (let b = a + 1; b < pool.length; b++) {
        const pair: [number, number] = [pool[a], pool[b]];
        const v = offerValue(matrix, s, pair, memo);
        raw.push({ pair, value: s.banked + v, regret: 0 });
      }
    }
  } else if (decision.kind === "forced") {
    const v = matrix[decision.ours][decision.theirs];
    raw.push({ ours: decision.ours, theirs: decision.theirs, value: s.banked + v, regret: 0 });
  }

  if (raw.length === 0) return raw;

  // Rank from the perspective of whoever owns the decision.
  const owner = "owner" in decision ? decision.owner : "our";
  const best =
    owner === "our"
      ? Math.max(...raw.map((o) => o.value))
      : Math.min(...raw.map((o) => o.value));
  for (const o of raw) o.regret = owner === "our" ? o.value - best : best - o.value;
  raw.sort((x, y) => y.regret - x.regret || y.value - x.value);
  return raw;
}

/** Value of a specific offer, once the attacking side picks from it. */
function offerValue(
  matrix: Matrix,
  s: LiveState,
  pair: [number, number],
  memo: Map<string, ProtocolResult>,
): number {
  // Same search the pick buttons show, minus what is already banked -- one
  // implementation, so the offer's headline value and the two halves beneath
  // it can never disagree on screen.
  const picks = pickOptions(matrix, s, pair, memo);
  const best = picks.find((p) => p.best)!;
  return best.value - s.banked;
}

/**
 * The two halves of an offer, valued.
 *
 * An offer is resolved by the *attacking* side choosing which of the pair they
 * face. When that side is us, this is a real decision of ours and the app owes
 * us a number for it -- the panel used to render two unlabelled buttons that
 * only said which player "was played", which is the right framing when we are
 * recording their choice and no help at all when the choice is ours.
 *
 * Found by playing a full round in a browser and tapping the first button at
 * every step: the round finished a point under the guaranteed floor, purely
 * because nothing on screen said which half to take.
 */
export interface PickOption {
  /** The player from the offered pair. */
  player: number;
  /** Final round total if this half is taken and play is perfect after it. */
  value: number;
  /** True for the half the attacking side should take. */
  best: boolean;
}

export function pickOptions(
  matrix: Matrix,
  s: LiveState,
  pair: [number, number],
  memo: Map<string, ProtocolResult> = new Map(),
): PickOption[] {
  const attackerIsUs = s.attackerSide === "our";

  const out: PickOption[] = pair.map((picked) => {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [s.attacker, picked] : [picked, s.attacker];
    const banked = matrix[ours][theirs];

    const nextOur = attackerIsUs ? s.ourPool : s.ourPool & ~(1 << picked) & ~(1 << leftover);
    const nextTheir = attackerIsUs
      ? s.theirPool & ~(1 << picked) & ~(1 << leftover)
      : s.theirPool;

    const rest =
      nextOur === 0 && nextTheir === 0
        ? 0
        : solveProtocol(
            matrix,
            {
              ourPool: nextOur,
              theirPool: nextTheir,
              attacker: leftover,
              attackerSide: attackerIsUs ? "their" : "our",
            },
            memo,
          ).value;

    return { player: picked, value: s.banked + banked + rest, best: false };
  });

  const target = attackerIsUs
    ? Math.max(...out.map((o) => o.value))
    : Math.min(...out.map((o) => o.value));
  for (const o of out) o.best = Math.abs(o.value - target) < 1e-9;
  return out;
}

/**
 * When both halves of an offer hold the same floor, what separates them.
 *
 * The guaranteed number is a minimax value, so on a tight board it ties
 * constantly -- and "either one is the same, take your pick" is not advice, it
 * is the app declining to answer. There is almost always signal underneath: two
 * halves with an identical floor can differ sharply in what they leave
 * reachable once the opponent plays their own board rather than hunting ours.
 *
 * Returns null when the halves genuinely do not tie (the floor already decided
 * it) or when the choice is not ours to make.
 *
 * The gap has to be *real*. `outlook` averages sampled opponent grids, so it
 * carries a sampling error, and printing a difference smaller than that error
 * would dress up noise as advice -- worse than saying nothing, because it looks
 * authoritative. `measure.tiebreak.test.ts` measured that error against a
 * 1500-trial reference over 155 real states:
 *
 *     trials |  p90 err |  max err | ms per call
 *         24 |    0.209 |    0.351 |         6.6
 *         96 |    0.096 |    0.191 |        27.1
 *        192 |    0.065 |    0.157 |        57.5
 *        384 |    0.040 |    0.105 |       112.5
 *
 * A tie-break runs two of these, so 96 trials keeps a tap near 54ms while
 * bounding each half's error at 0.191 -- 0.382 for the pair in the worst case.
 * MIN_REAL_GAP sits just above that, so any gap this prints survived the noise.
 */
export interface PickTieBreak {
  /** The half to take. */
  player: number;
  /** The half not taken. */
  other: number;
  /**
   * Which instrument separated them, or `interchangeable` when nothing did
   * because nothing could -- see that rung for why it is an answer, not a
   * shrug.
   */
  reason: "typical" | "upside" | "pressure" | "average" | "interchangeable";
  /** The figure that decided it, for the taken half. Unused when interchangeable. */
  value: number;
  /** The same figure for the half not taken. Unused when interchangeable. */
  otherValue: number;
}

/** Sampled grids per half when breaking a tie. See the table above. */
const TIEBREAK_TRIALS = 96;

/**
 * Smallest gap in typical value worth printing, set above the worst case of
 * two independent 96-trial errors (0.191 each). Below this the halves are
 * genuinely indistinguishable on this instrument and we say so rather than
 * inventing a reason.
 *
 * Only the sampled rung needs a threshold. The upside and pressure rungs are
 * computed exactly from the board, so any difference in them is real.
 */
const MIN_REAL_GAP = 0.4;

export function pickTieBreak(
  matrix: Matrix,
  s: LiveState,
  pair: [number, number],
): PickTieBreak | null {
  if (s.attackerSide !== "our") return null;

  const picks = pickOptions(matrix, s, pair);
  if (Math.abs(picks[0].value - picks[1].value) > 1e-9) return null;

  const scored = picks.map((p) => {
    const leftover = p.player === pair[0] ? pair[1] : pair[0];
    const after = commitPairing(matrix, s, s.attacker, p.player, leftover, "their");

    if (currentDecision(after).kind === "done") {
      return {
        player: p.player,
        typical: after.banked,
        ceiling: after.banked,
        meanReply: after.banked,
        // Nothing left for them to get wrong, so nothing can punish us.
        punishRate: 0,
      };
    }

    const view = outlook(
      matrix,
      {
        ourPool: after.ourPool,
        theirPool: after.theirPool,
        attacker: after.attacker,
        attackerSide: after.attackerSide,
      },
      p.value - after.banked,
      TIEBREAK_TRIALS,
    );

    // Deterministic: every reply they could make, valued exactly. `ceiling` is
    // what we collect if they slip; `punishRate` is how much of their reply
    // space actually holds us to the floor.
    const replies = moveOptions(matrix, after);
    const values = replies.map((r) => r.value);
    const worst = Math.min(...values);
    return {
      player: p.player,
      typical: after.banked + view.expected,
      ceiling: Math.max(...values),
      meanReply: values.reduce((sum, v) => sum + v, 0) / values.length,
      punishRate: values.filter((v) => Math.abs(v - worst) < 1e-9).length / values.length,
    };
  });

  const [a, b] = scored;

  // Rung 2: what it typically plays out to, if they play their own board
  // rather than hunting ours. Sampled, so it must clear the noise floor.
  if (Math.abs(a.typical - b.typical) >= MIN_REAL_GAP) {
    const [win, lose] = a.typical > b.typical ? [a, b] : [b, a];
    return {
      player: win.player,
      other: lose.player,
      reason: "typical",
      value: win.typical,
      otherValue: lose.typical,
    };
  }

  // Rung 3: play to your outs. Same floor, same typical -- but one half keeps a
  // bigger prize alive if they misplay. Exact, so any difference counts.
  if (Math.abs(a.ceiling - b.ceiling) > 1e-9) {
    const [win, lose] = a.ceiling > b.ceiling ? [a, b] : [b, a];
    return {
      player: win.player,
      other: lose.player,
      reason: "upside",
      value: win.ceiling,
      otherValue: lose.ceiling,
    };
  }

  // Rung 4: identical floor, typical and ceiling -- so the separator is how
  // much of their reply space actually punishes us. Fewer punishing replies
  // means more of their plausible answers leave us better than the floor.
  if (Math.abs(a.punishRate - b.punishRate) > 1e-9) {
    const [win, lose] = a.punishRate < b.punishRate ? [a, b] : [b, a];
    return {
      player: win.player,
      other: lose.player,
      reason: "pressure",
      value: win.punishRate,
      otherValue: lose.punishRate,
    };
  }

  // Rung 5: identical floor, typical, ceiling and punish rate -- so compare the
  // whole reply space rather than just its ends. Exact. This catches halves
  // whose extremes match but whose middles do not.
  if (Math.abs(a.meanReply - b.meanReply) > 1e-9) {
    const [win, lose] = a.meanReply > b.meanReply ? [a, b] : [b, a];
    return {
      player: win.player,
      other: lose.player,
      reason: "average",
      value: win.meanReply,
      otherValue: lose.meanReply,
    };
  }

  // Terminal rung: nothing separated them, so check whether anything *could*.
  // If the two carry the same ratings against every player we still hold, they
  // are interchangeable on this board and no instrument will ever split them.
  //
  // Measured on the five real WTC boards: 145 of 242 unseparated ties (60%) are
  // this case. Saying so is an answer -- it tells the user their own grid has
  // no opinion left, so anything they know off-sheet decides it. Staying silent
  // implies the app checked and found nothing, which is a different claim.
  if (sameAgainstOurPool(matrix, s, picks[0].player, picks[1].player)) {
    return {
      player: picks[0].player,
      other: picks[1].player,
      reason: "interchangeable",
      value: 0,
      otherValue: 0,
    };
  }

  return null;
}

/**
 * Do these two of their players carry identical ratings against everyone we
 * still have, including the player currently put forward?
 *
 * The attacker is included because they are about to play one of the two, so
 * their row is part of what makes the halves comparable.
 */
function sameAgainstOurPool(matrix: Matrix, s: LiveState, x: number, y: number): boolean {
  const live = s.ourPool | (1 << s.attacker);
  for (let r = 0; r < matrix.length; r++) {
    if (!(live & (1 << r))) continue;
    if (Math.abs(matrix[r][x] - matrix[r][y]) > 1e-9) return false;
  }
  return true;
}

/**
 * Commit a pairing and hand the initiative to the leftover player's side.
 *
 * The pool means "unpaired and not currently put forward", matching the solver.
 * The declined player therefore leaves their pool and is carried as `attacker`;
 * leaving them in both would let the same player be paired twice.
 */
export function commitPairing(
  matrix: Matrix,
  s: LiveState,
  ours: number,
  theirs: number,
  leftover: number | null,
  leftoverSide: Side | null,
): LiveState {
  const value = matrix[ours][theirs];
  let ourPool = s.ourPool & ~(1 << ours);
  let theirPool = s.theirPool & ~(1 << theirs);

  const carries = leftover !== null && leftoverSide !== null;
  if (carries) {
    if (leftoverSide === "our") ourPool &= ~(1 << leftover);
    else theirPool &= ~(1 << leftover);
  }

  return {
    ourPool,
    theirPool,
    attacker: carries ? (leftover as number) : -1,
    attackerSide: carries ? (leftoverSide as Side) : s.attackerSide,
    banked: s.banked + value,
    committed: [...s.committed, { ours, theirs, value }],
  };
}

/** What holding a player back is worth, in points. */
export interface Leverage {
  player: number;
  /** Best guaranteed total with this player paired at the next opportunity. */
  ifPlayedNow: number;
  /** Best guaranteed total with this player held back instead. */
  ifHeld: number;
  /** Positive means waiting pays; negative means the opportunity is now. */
  gainFromWaiting: number;
}

/**
 * Per-player value of waiting.
 *
 * This is the answer to "hold Pete or hold Bokur". It does not rank players by
 * how good their matchups look; it searches the rest of the round twice for
 * each player -- once committing them at the next opportunity, once refusing
 * to -- and reports the difference. A player with a large positive gain has
 * opportunities later that do not exist now. A player with a negative gain is
 * a player whose moment is this one.
 */
export function playerLeverage(matrix: Matrix, s: LiveState): Leverage[] {
  const options = moveOptions(matrix, s);
  if (options.length === 0) return [];

  const out: Leverage[] = [];
  for (const p of bits(s.ourPool)) {
    const uses: number[] = [];
    const holds: number[] = [];
    for (const o of options) {
      const involves =
        o.ours === p || (o.pair !== undefined && isOurOffer(s) && o.pair.includes(p));
      (involves ? uses : holds).push(o.value);
    }
    if (uses.length === 0 || holds.length === 0) continue;
    const ifPlayedNow = Math.max(...uses);
    const ifHeld = Math.max(...holds);
    out.push({ player: p, ifPlayedNow, ifHeld, gainFromWaiting: ifHeld - ifPlayedNow });
  }
  out.sort((a, b) => b.gainFromWaiting - a.gainFromWaiting);
  return out;
}

function isOurOffer(s: LiveState): boolean {
  const d = currentDecision(s);
  return d.kind === "offer" && d.owner === "our";
}

/**
 * What an option is worth across the whole range of their replies.
 *
 * The guaranteed number is a minimax value, so on a tight board every option
 * often reports the same figure -- their best reply caps all of them equally.
 * That is not "the decision does not matter"; it is one statistic being asked
 * to carry more than it can.
 *
 * This looks at the same options a second way. For each of our moves it
 * enumerates every reply they have and records the spread:
 *
 *  - `guaranteed` is unchanged: what we hold if they answer perfectly.
 *  - `ifTheyErr` is what we get from their *worst* reply. This is the upside
 *    that is genuinely on the table -- the "play to your outs" number.
 *  - `punishingReplies` counts how many of their replies actually hold us to
 *    the guaranteed figure. One punishing reply out of ten is a very different
 *    proposition from nine out of ten, even though minimax scores them alike.
 *
 * Two options with identical guaranteed values can differ sharply here, and
 * that difference is the tie-break the app has never been able to show.
 */
export interface OptionProfile {
  guaranteed: number;
  ifTheyErr: number;
  punishingReplies: number;
  totalReplies: number;
  /** Upside surrendered if they answer perfectly. */
  upside: number;
}

export function optionProfile(
  matrix: Matrix,
  s: LiveState,
  opt: MoveOption,
): OptionProfile | null {
  const next = stateAfterOption(s, opt, matrix);
  if (!next) return null;

  const replies = moveOptions(matrix, next);
  if (replies.length === 0) return null;

  const values = replies.map((r) => r.value);
  const guaranteed = Math.min(...values);
  const ifTheyErr = Math.max(...values);
  const punishingReplies = values.filter((v) => Math.abs(v - guaranteed) < 1e-9).length;

  return {
    guaranteed,
    ifTheyErr,
    punishingReplies,
    totalReplies: values.length,
    upside: ifTheyErr - guaranteed,
  };
}

/**
 * The state we hand them after taking `opt`.
 *
 * Only defined for moves that pass the initiative straight to them; an offer we
 * make is resolved by their pick, which `offerValue` already searches, so there
 * is no single successor state to profile.
 */
function stateAfterOption(s: LiveState, opt: MoveOption, matrix: Matrix): LiveState | null {
  const d = currentDecision(s);

  if (d.kind === "open" && d.owner === "our" && opt.ours !== undefined) {
    return {
      ...s,
      ourPool: s.ourPool & ~(1 << opt.ours),
      attacker: opt.ours,
      attackerSide: "our",
    };
  }

  if (d.kind === "pick" && opt.ours !== undefined && opt.theirs !== undefined) {
    const leftover = d.pair[0] === (d.attackerSide === "our" ? opt.theirs : opt.ours)
      ? d.pair[1]
      : d.pair[0];
    return commitPairing(
      matrix,
      s,
      opt.ours,
      opt.theirs,
      leftover,
      d.attackerSide === "our" ? "their" : "our",
    );
  }

  return null;
}

