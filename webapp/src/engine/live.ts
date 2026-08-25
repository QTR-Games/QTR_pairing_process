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
  const attackerIsUs = s.attackerSide === "our";
  let best = attackerIsUs ? -Infinity : Infinity;

  for (const picked of pair) {
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

    const total = banked + rest;
    if (attackerIsUs ? total > best : total < best) best = total;
  }
  return best;
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

