/**
 * The invariant the whole screen rests on.
 *
 * `Verdict` prints a guaranteed total from `protocolFloor`. `LivePanel` then
 * walks you through the round using `moveOptions`. Those are two separate code
 * paths reading the same matrix, and nothing has ever checked that they agree.
 *
 * They must. If you follow the advice at every decision that is yours, and they
 * answer perfectly at every decision that is theirs, the round has to finish on
 * exactly the number the verdict promised. A guaranteed floor you can drop below
 * by doing what the app told you is not a floor -- it is a lie with a caption.
 *
 * This was found by driving a real round in a browser: the verdict said 15 and
 * following the top option landed on 14.
 */

import { describe, expect, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";
import { commitPairing, currentDecision, moveOptions, newRound } from "./live";
import type { LiveState } from "./live";
import { protocolFloor } from "./protocol";

const REAL = boards as unknown as { opponent: string; matrix: number[][] }[];

/**
 * Play the round out with both sides perfect.
 *
 * At an offer, the offering side names a pair and the *attacking* side picks
 * from it -- so the pick is resolved by searching, exactly as `offerValue`
 * does, rather than by taking the first listed option.
 */
function playPerfect(matrix: Matrix, ourTeamFirst: boolean): LiveState {
  let s = newRound(matrix.length, ourTeamFirst);

  for (let guard = 0; guard < 64; guard++) {
    const d = currentDecision(s);
    if (d.kind === "done") return s;

    if (d.kind === "forced") {
      s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
      continue;
    }

    const opts = moveOptions(matrix, s);
    expect(opts.length).toBeGreaterThan(0);

    // moveOptions ranks from the mover's own perspective, best first.
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

    // An offer: the attacker chooses which of the pair to take.
    const pair = best.pair!;
    const attackerIsUs = s.attackerSide === "our";
    let chosen = pair[0];
    let chosenValue = attackerIsUs ? -Infinity : Infinity;

    for (const candidate of pair) {
      const leftover = candidate === pair[0] ? pair[1] : pair[0];
      const [ours, theirs] = attackerIsUs
        ? [s.attacker, candidate]
        : [candidate, s.attacker];
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

  throw new Error("round did not terminate");
}

describe("the advice and the promise are the same number", () => {
  for (const ourTeamFirst of [true, false]) {
    const who = ourTeamFirst ? "we open" : "they open";

    it(`lands exactly on the guaranteed floor when ${who}`, () => {
      for (const b of REAL) {
        const promised = protocolFloor(b.matrix, ourTeamFirst).value;
        const played = playPerfect(b.matrix, ourTeamFirst);

        expect(played.committed).toHaveLength(b.matrix.length);
        expect(played.banked).toBeCloseTo(promised, 9);
      }
    });
  }

  it("never drops below the floor, whatever they do, if we follow the advice", () => {
    // Ours perfect, theirs adversarial in a different way: they take their
    // *worst*-ranked reply. The floor is a floor -- it may only be beaten.
    for (const b of REAL) {
      const matrix = b.matrix;
      const promised = protocolFloor(matrix, true).value;
      let s = newRound(matrix.length, true);

      for (let guard = 0; guard < 64; guard++) {
        const d = currentDecision(s);
        if (d.kind === "done") break;
        if (d.kind === "forced") {
          s = commitPairing(matrix, s, d.ours, d.theirs, null, null);
          continue;
        }

        const opts = moveOptions(matrix, s);
        const opt = d.owner === "our" ? opts[0] : opts[opts.length - 1];

        if (d.kind === "open") {
          const p = d.owner === "our" ? opt.ours! : opt.theirs!;
          s = {
            ...s,
            ourPool: d.owner === "our" ? s.ourPool & ~(1 << p) : s.ourPool,
            theirPool: d.owner === "their" ? s.theirPool & ~(1 << p) : s.theirPool,
            attacker: p,
            attackerSide: d.owner,
          };
          continue;
        }

        const pair = opt.pair!;
        const attackerIsUs = s.attackerSide === "our";

        // The attacker picks from the pair. When that is us, "following the
        // advice" means taking the better half -- picking arbitrarily here is
        // not following anything, and would test our own coin-flip instead.
        let chosen = pair[0];
        if (attackerIsUs) {
          let bestValue = -Infinity;
          for (const candidate of pair) {
            const other = candidate === pair[0] ? pair[1] : pair[0];
            const after = commitPairing(matrix, s, s.attacker, candidate, other, "their");
            const rest =
              currentDecision(after).kind === "done"
                ? after.banked
                : moveOptions(matrix, after)[0].value;
            if (rest > bestValue) {
              bestValue = rest;
              chosen = candidate;
            }
          }
        }

        const leftover = chosen === pair[0] ? pair[1] : pair[0];
        const [ours, theirs] = attackerIsUs
          ? [s.attacker, chosen]
          : [chosen, s.attacker];
        s = commitPairing(matrix, s, ours, theirs, leftover, attackerIsUs ? "their" : "our");
      }

      expect(s.banked).toBeGreaterThanOrEqual(promised - 1e-9);
    }
  });
});
