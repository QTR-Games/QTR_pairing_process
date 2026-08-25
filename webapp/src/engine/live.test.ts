/**
 * The live advisor is what the phone actually shows at a table, so the thing
 * worth proving is that it never disagrees with the solver underneath it.
 *
 * The strong test here is `following the advice reproduces the solver value`:
 * it plays whole rounds move by move through the same code path the UI uses,
 * with the opponent playing their best reply, and checks the banked total lands
 * exactly on `protocolFloor`. If the advisor ever recommended a move that gave
 * something away, or the commit bookkeeping drifted, that number would move.
 */
import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { protocolFloor } from "./protocol";
import {
  commitPairing,
  currentDecision,
  moveOptions,
  newRound,
  playerLeverage,
  type LiveState,
} from "./live";

/** Play a full round, both sides taking the advisor's top-ranked move. */
function playOut(matrix: Matrix, ourTeamFirst: boolean): LiveState {
  let s = newRound(matrix.length, ourTeamFirst);
  let guard = 0;

  while (guard++ < 50) {
    const d = currentDecision(s);
    if (d.kind === "done") break;
    if (d.kind === "forced") {
      s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
      continue;
    }

    const best = moveOptions(matrix, s)[0];
    expect(best).toBeDefined();

    if (d.kind === "open") {
      // Opening only puts a player forward; nothing is paired yet.
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

    // An offer: the attacking side then picks from the pair.
    const pair = best.pair!;
    const attackerIsUs = d.attackerSide === "our";
    let chosen = pair[0];
    let chosenValue = attackerIsUs ? -Infinity : Infinity;

    for (const candidate of pair) {
      const leftover = candidate === pair[0] ? pair[1] : pair[0];
      const [ours, theirs] = attackerIsUs ? [s.attacker, candidate] : [candidate, s.attacker];
      const after = commitPairing(
        matrix,
        s,
        ours,
        theirs,
        leftover,
        attackerIsUs ? "their" : "our",
      );
      const rest =
        currentDecision(after).kind === "done"
          ? after.banked
          : moveOptions(matrix, after)[0].value;
      if (attackerIsUs ? rest > chosenValue : rest < chosenValue) {
        chosenValue = rest;
        chosen = candidate;
      }
    }

    const leftover = chosen === pair[0] ? pair[1] : pair[0];
    const [ours, theirs] = attackerIsUs ? [s.attacker, chosen] : [chosen, s.attacker];
    s = commitPairing(matrix, s, ours, theirs, leftover, attackerIsUs ? "their" : "our");
  }
  return s;
}

const REAL = boards as unknown as { opponent: string; matrix: number[][] }[];

describe("live advisor", () => {
  it("resolves a 5v5 round into exactly five pairings", () => {
    const final = playOut(REAL[0].matrix, true);
    expect(final.committed).toHaveLength(5);
    expect(final.ourPool).toBe(0);
    expect(final.theirPool).toBe(0);
  });

  it("pairs every player exactly once", () => {
    const final = playOut(REAL[0].matrix, true);
    expect(new Set(final.committed.map((c) => c.ours)).size).toBe(5);
    expect(new Set(final.committed.map((c) => c.theirs)).size).toBe(5);
  });

  it("banks the sum of the pairings it committed", () => {
    const final = playOut(REAL[3].matrix, true);
    const sum = final.committed.reduce((a, c) => a + c.value, 0);
    expect(final.banked).toBe(sum);
  });

  it("following the advice reproduces the solver value, on every real board", () => {
    for (const b of REAL) {
      for (const ourTeamFirst of [true, false]) {
        const final = playOut(b.matrix, ourTeamFirst);
        expect(final.committed).toHaveLength(5);
        expect(final.banked).toBe(protocolFloor(b.matrix, ourTeamFirst).value);
      }
    }
  });

  it("ranks the best move at zero regret and never above it", () => {
    const s = newRound(5, true);
    const opts = moveOptions(REAL[0].matrix, s);
    expect(opts.length).toBeGreaterThan(0);
    expect(Math.max(...opts.map((o) => o.regret))).toBe(0);
    expect(opts[0].regret).toBe(0);
  });

  it("routes the opening decision to whoever is putting a player forward", () => {
    expect(currentDecision(newRound(5, true))).toEqual({ kind: "open", owner: "our" });
    expect(currentDecision(newRound(5, false))).toEqual({ kind: "open", owner: "their" });
  });

  it("hands the initiative to the declined player's own side", () => {
    const matrix = REAL[0].matrix;
    let s = newRound(5, true);
    s = { ...s, ourPool: s.ourPool & ~1, attacker: 0, attackerSide: "our" };
    // We are forward, so they offer; we pick 1 and decline 2.
    const after = commitPairing(matrix, s, 0, 1, 2, "their");
    expect(after.attacker).toBe(2);
    expect(after.attackerSide).toBe("their");
    // The declined player is carried as the attacker, not left in the pool,
    // or they could be paired a second time.
    expect(after.theirPool & (1 << 2)).toBe(0);
    expect(after.theirPool & (1 << 1)).toBe(0);
    expect(after.theirPool).toBe((1 << 0) | (1 << 3) | (1 << 4));
  });

  it("reports the value of holding a player back", () => {
    const lev = playerLeverage(REAL[0].matrix, newRound(5, true));
    expect(lev).toHaveLength(5);
    for (const l of lev) {
      expect(l.gainFromWaiting).toBe(l.ifHeld - l.ifPlayedNow);
    }
    // Sorted best-to-worst reason to wait.
    for (let i = 1; i < lev.length; i++) {
      expect(lev[i - 1].gainFromWaiting).toBeGreaterThanOrEqual(lev[i].gainFromWaiting);
    }
  });

  it("finds boards where holding a player is worth real points", () => {
    let separating = 0;
    for (const b of REAL) {
      const lev = playerLeverage(b.matrix, newRound(5, true));
      const spread = lev[0].gainFromWaiting - lev[lev.length - 1].gainFromWaiting;
      if (spread > 0) separating++;
    }
    // If this were zero the feature would be telling the user nothing.
    expect(separating).toBeGreaterThan(0);
  });
});
