/**
 * A shared search cache must change the cost and nothing else.
 *
 * `SolveCache` exists because the solver was being asked the same question
 * repeatedly and forbidden from remembering the answer: `moveOptions` allocated
 * a fresh memo on entry, `playerLeverage` re-entered it for the same state, and
 * `optionProfile` re-entered it once per option on screen.
 *
 * That makes this a dangerous kind of change. A memo that returns a stale or
 * foreign answer does not crash -- it quietly advises a different pairing, and
 * the only symptom is a lost round weeks later. So the equivalence is asserted
 * over every real board rather than argued from the code.
 *
 * The second risk is the reason `SolveCache` carries its matrix at all. The
 * memo key is `ourPool|theirPool|attacker|attackerSide` and omits the board,
 * because putting 25 numbers in a string key would cost more than the lookup
 * saves. That makes a cache reused across boards silently wrong, so misuse is
 * made loud instead.
 */
import { describe, expect, it } from "vitest";
import type { Matrix } from "./boardAnalysis";
import {
  commitPairing,
  currentDecision,
  moveOptions,
  newRound,
  optionProfile,
  pickOptions,
  playerLeverage,
} from "./live";
import { solveCache } from "./protocol";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];

/**
 * Walk a whole round, collecting every number the panel would draw.
 *
 * Deliberately records values AND ordering: the ranking is what the user acts
 * on, so a cache that preserved the numbers but reshuffled the rows would be a
 * real regression and this has to catch it.
 */
function transcript(matrix: Matrix, ourTeamFirst: boolean, shared: boolean): string[] {
  const cache = shared ? solveCache(matrix) : undefined;
  let s = newRound(matrix.length, ourTeamFirst);
  const out: string[] = [];
  let guard = 0;

  while (guard++ < 40) {
    const d = currentDecision(s);
    if (d.kind === "done") break;

    const opts = moveOptions(matrix, s, cache);
    out.push(
      `${d.kind}|` +
        opts
          .map((o) => `${o.ours ?? "-"}/${o.theirs ?? "-"}/${o.pair?.join("+") ?? "-"}=${o.value.toFixed(6)}@${o.regret.toFixed(6)}`)
          .join(","),
    );

    for (const l of playerLeverage(matrix, s, cache)) {
      out.push(`lev ${l.player} ${l.ifPlayedNow.toFixed(6)} ${l.ifHeld.toFixed(6)}`);
    }

    for (const o of opts) {
      const p = optionProfile(matrix, s, o, cache);
      if (p) out.push(`prof ${p.guaranteed.toFixed(6)} ${p.ifTheyErr.toFixed(6)} ${p.punishingReplies}/${p.totalReplies}`);
      if (o.pair) {
        const picks = pickOptions(matrix, s, o.pair, cache);
        out.push(`pick ${picks.map((x) => `${x.player}=${x.value.toFixed(6)}${x.best ? "*" : ""}`).join(",")}`);
      }
    }

    if (d.kind === "forced") {
      s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
      continue;
    }

    const best = opts[0];
    if (d.kind === "open") {
      const p = d.owner === "our" ? best.ours! : best.theirs!;
      s = {
        ...s,
        ourPool: d.owner === "our" ? s.ourPool & ~(1 << p) : s.ourPool,
        theirPool: d.owner === "their" ? s.theirPool & ~(1 << p) : s.theirPool,
        attacker: p,
        attackerSide: d.owner,
      };
      continue;
    }

    const pair = best.pair!;
    const attackerIsUs = d.attackerSide === "our";
    const [ours, theirs] = attackerIsUs ? [s.attacker, pair[0]] : [pair[0], s.attacker];
    s = commitPairing(matrix, s, ours, theirs, pair[1], attackerIsUs ? "their" : "our");
  }

  return out;
}

describe("shared solve cache", () => {
  it("gives byte-identical advice on every real board, from both openings", () => {
    for (const f of FIXTURES) {
      for (const first of [true, false]) {
        expect(
          transcript(f.matrix, first, true),
          `${f.opponent}, ${first ? "we open" : "they open"}`,
        ).toEqual(transcript(f.matrix, first, false));
      }
    }
  });

  it("refuses a cache built for a different board", () => {
    const a = FIXTURES[0].matrix;
    const b = FIXTURES[1].matrix;
    const cache = solveCache(a);
    const s = newRound(a.length, true);

    expect(() => moveOptions(b, s, cache)).toThrow(/different board/i);
    expect(() => playerLeverage(b, s, cache)).toThrow(/different board/i);
  });

  /**
   * Reference equality, not deep equality. Two structurally identical boards
   * are still two boards to a caller, and a deep compare on every call would
   * cost more than the memo saves.
   */
  it("refuses a structurally identical copy, because identity is the contract", () => {
    const a = FIXTURES[0].matrix;
    const copy = a.map((row) => [...row]);
    const cache = solveCache(a);
    const s = newRound(a.length, true);

    expect(() => moveOptions(copy, s, cache)).toThrow(/different board/i);
  });

  it("actually retains work across calls rather than silently starting over", () => {
    const m = FIXTURES[0].matrix;
    const cache = solveCache(m);
    const s = newRound(m.length, true);

    moveOptions(m, s, cache);
    const afterFirst = cache.memo.size;
    expect(afterFirst).toBeGreaterThan(0);

    // The same question again must add nothing: every state it visits is known.
    moveOptions(m, s, cache);
    expect(cache.memo.size).toBe(afterFirst);
  });

  it("stays valid as the round narrows, which is why it is scoped to the board", () => {
    const m = FIXTURES[0].matrix;
    const cache = solveCache(m);
    const root = newRound(m.length, true);

    const opener = moveOptions(m, root, cache)[0];
    const after = {
      ...root,
      ourPool: root.ourPool & ~(1 << opener.ours!),
      attacker: opener.ours!,
      attackerSide: "our" as const,
    };

    // A cache carried across a commit must agree with a cold search of the
    // same state -- this is the reuse the panel depends on between taps.
    expect(moveOptions(m, after, cache)).toEqual(moveOptions(m, after));
  });
});
