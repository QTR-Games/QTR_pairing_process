/**
 * The demo set is a marketing surface as much as a feature, which is exactly
 * why it needs tests.
 *
 * Each of the three boards was chosen because the engine does something
 * specific and checkable on it, and those three behaviours are the things the
 * app claims about itself. A board that quietly stopped demonstrating its point
 * -- because a threshold moved, or the sampler was retuned -- would leave the
 * demo showing nothing while still looking fine. So every board asserts the
 * property it was picked for, and the numbers quoted in `teaches` are asserted
 * rather than described.
 */

import { describe, expect, it } from "vitest";
import {
  assignmentExtremes,
  cellOutlooks,
  decisionReport,
  evenThreshold,
  type Matrix,
} from "../engine/boardAnalysis";
import { chanceOutlook } from "../engine/opponent";
import { protocolFloor } from "../engine/protocol";
import {
  boardMatrix,
  boardScale,
  emptyBoard,
  isRated,
  isValidBoard,
  saveBoard,
  TEAM_SIZE,
} from "./board";
import { DEMO_IDS, demoBoards, installDemoBoards, isDemoBoard } from "./demoBoards";
import { resetStore, setStore } from "./store";

const byKey = (key: string) => {
  const found = demoBoards().find((d) => d.key === key);
  if (!found) throw new Error(`no demo board ${key}`);
  return found;
};

const matrixOf = (key: string): Matrix => {
  const { board } = byKey(key);
  return boardMatrix(board, boardScale(board));
};

const openingState = (n: number) => ({
  ourPool: (1 << n) - 1,
  theirPool: (1 << n) - 1,
  attacker: -1,
  attackerSide: "our" as const,
});

/** The dead-even line for a five-game round on the 1-5 scale. */
const TAU = evenThreshold(TEAM_SIZE, 1, 5);

describe("the demo set", () => {
  it("is three valid, rated, distinct boards", () => {
    const demos = demoBoards();
    expect(demos).toHaveLength(3);

    for (const { board, title, teaches } of demos) {
      expect(isValidBoard(board), title).toBe(true);
      // Without `touched` these read as untouched, which gates autosave and
      // leaves the verdict with nothing to say -- the demo would open blank.
      expect(isRated(board), title).toBe(true);
      expect(board.ourPlayers).toHaveLength(TEAM_SIZE);
      expect(board.theirPlayers).toHaveLength(TEAM_SIZE);
      expect(board.opponent.trim().length, title).toBeGreaterThan(0);
      expect(teaches.trim().length, title).toBeGreaterThan(0);

      for (const row of board.fractions) {
        for (const f of row) {
          expect(f).toBeGreaterThanOrEqual(0);
          expect(f).toBeLessThanOrEqual(1);
        }
      }
    }

    const ids = demos.map((d) => d.board.id);
    expect(new Set(ids).size).toBe(ids.length);
    // Stable ids, so loading the demo twice replaces rather than duplicates.
    expect(ids).toEqual([...DEMO_IDS]);
    expect(demos.every((d) => isDemoBoard(d.board))).toBe(true);
  });

  it("installs in definition order, and re-installing refreshes rather than duplicates", () => {
    const mem = new Map<string, string>();
    setStore({
      getItem: (k) => mem.get(k) ?? null,
      setItem: (k, v) => void mem.set(k, v),
      removeItem: (k) => void mem.delete(k),
    });

    try {
      const first = installDemoBoards();
      expect(first).toHaveLength(3);
      expect(first.map((b) => b.id)).toEqual([...DEMO_IDS]);

      // The button someone presses when they are not sure what it does. Pressing
      // it twice must not leave six boards behind.
      const second = installDemoBoards();
      expect(second).toHaveLength(3);
      expect(second.map((b) => b.id)).toEqual([...DEMO_IDS]);
      expect(second.filter(isDemoBoard)).toHaveLength(3);
    } finally {
      resetStore();
    }
  });

  it("leaves boards the owner already had alone", () => {
    const mem = new Map<string, string>();
    setStore({
      getItem: (k) => mem.get(k) ?? null,
      setItem: (k, v) => void mem.set(k, v),
      removeItem: (k) => void mem.delete(k),
    });

    try {
      const mine = { ...emptyBoard(), id: "mine", opponent: "Real opponent" };
      saveBoard(mine);

      const after = installDemoBoards();
      expect(after).toHaveLength(4);
      expect(after.some((b) => b.id === "mine")).toBe(true);
      /*
        The demo set keeps its defined order relative to itself. Where it lands
        against boards the owner already had is left to the saved list's own
        recency rule rather than asserted here: a board saved in the same
        millisecond as the install ties on `updatedAt`, which makes an exact
        top-three assertion a coin toss rather than a real guarantee.
      */
      expect(after.filter(isDemoBoard).map((b) => b.id)).toEqual([...DEMO_IDS]);
    } finally {
      resetStore();
    }
  });

  it("round-trips the captured ratings through the stored fractions", () => {
    // The ratings are stored as fractions, so a demo board read back on its own
    // scale must give the integers that were captured. If this drifts, the
    // boards below stop being the boards the thresholds were measured on.
    expect(matrixOf("demo-too-close")).toEqual([
      [3, 3, 2, 3, 3],
      [3, 3, 2, 2, 2],
      [3, 3, 3, 3, 3],
      [2, 3, 3, 3, 3],
      [3, 3, 1, 3, 3],
    ]);
  });

  /*
    Board 1. The honesty claim.

    Nineteen of twenty-five cells carry the same rating, so there is almost no
    shape for a pairing decision to exploit. Verdict.tsx calls this too close to
    call when the typical outcome sits inside two standard errors of a coin
    flip, and this board is the reason that guard is worth having: a tool that
    ranks pairings on one number will happily name a best move here.
  */
  it("has a board the engine refuses to call", () => {
    const m = matrixOf("demo-too-close");
    const chance = chanceOutlook(m, openingState(m.length), 0, 1, 5);

    // The exact branch Verdict.tsx takes.
    const tooCloseToCall = Math.abs(chance.expected - 0.5) < 2 * chance.stderr;
    expect(tooCloseToCall).toBe(true);

    // And it is genuinely flat rather than merely noisy.
    const cells = m.flat();
    const commonest = Math.max(
      ...[...new Set(cells)].map((v) => cells.filter((x) => x === v).length),
    );
    expect(commonest).toBeGreaterThanOrEqual(19);
  });

  /*
    Board 2. The false-tie claim.

    Several pairings share the best reachable ceiling, so any ranking that reads
    only the best case treats them as interchangeable. They are not: the
    guaranteed floor across that tied set spans four points, which is more than
    the whole margin between a won and a lost round on this scale.

    Note `choiceMatters` is deliberately false here, and that is the point
    rather than a weakness. It means no pairing on the frontier trades floor
    against ceiling -- there is a single best cell, and nothing has to be given
    up to take it. A tool that ranks on the ceiling alone still cannot find it,
    because every candidate it can see looks the same. The information is on the
    floor, and the floor is the axis a one-number ranking throws away.
  */
  it("has a board where equal-looking pairings differ by four guaranteed points", () => {
    const m = matrixOf("demo-false-tie");
    const report = decisionReport(m, TAU);

    expect(report.hiddenFloorCost).toBeGreaterThanOrEqual(4);

    // The tie has to be real for the claim to mean anything: more than one
    // pairing must actually share that best ceiling.
    const cells = [...cellOutlooks(m, TAU).values()];
    const bestCeiling = Math.max(...cells.map((c) => c.ceiling));
    const tied = cells.filter((c) => c.ceiling === bestCeiling);
    expect(tied.length).toBeGreaterThan(1);

    // No floor-versus-ceiling trade-off exists, so the right pick costs nothing
    // -- it is only invisible to a ranking that never reads the floor.
    expect(report.choiceMatters).toBe(false);
    expect(
      Math.max(...tied.map((c) => c.floor)) - Math.min(...tied.map((c) => c.floor)),
    ).toBeGreaterThanOrEqual(4);
  });

  /*
    Board 3. The protocol claim, and the sharpest of the three.

    The best matching on this board scores 18 against a dead-even line of 15, so
    a tool that optimises over matchings reports a comfortable win. You do not
    get to choose the matching: the opponent answers half the nominations, and
    what survives that is 15 -- exactly even. The three-point drop is the part a
    permutation-only view cannot express, and it is the difference between
    "winning" and "coin flip".
  */
  it("has a board where the best matching is three points better than anything holdable", () => {
    const m = matrixOf("demo-optimistic-matching");
    const [assignmentFloor, assignmentCeiling] = assignmentExtremes(m);

    const opening = protocolFloor(m, true).value;
    const receiving = protocolFloor(m, false).value;
    const holdable = Math.max(opening, receiving);

    expect(assignmentCeiling).toBe(18);
    expect(assignmentFloor).toBe(10);
    expect(holdable).toBe(15);
    expect(assignmentCeiling - holdable).toBeGreaterThanOrEqual(3);

    // The claim in `teaches`: the paper matching wins, the guarantee is level.
    expect(assignmentCeiling).toBeGreaterThan(TAU);
    expect(holdable).toBeLessThanOrEqual(TAU);

    // And the dice-off is a real decision here rather than a formality.
    expect(receiving).toBeGreaterThan(opening);
  });

  it("never promises more than the protocol can hold, on any demo board", () => {
    // A guard against someone later swapping in a board that flatters the app.
    for (const { board, title } of demoBoards()) {
      const m = boardMatrix(board, boardScale(board));
      const [, ceiling] = assignmentExtremes(m);
      const holdable = Math.max(protocolFloor(m, true).value, protocolFloor(m, false).value);
      expect(holdable, title).toBeLessThanOrEqual(ceiling);
    }
  });
});
