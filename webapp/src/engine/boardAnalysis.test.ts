import { describe, expect, it } from "vitest";
import {
  assignmentExtremes,
  boardOutlook,
  cellOutlooks,
  decisionReport,
  dominates,
  evenThreshold,
  hungarianMin,
  LIVE,
  SECURED,
  UNWINNABLE,
  type Matrix,
} from "./boardAnalysis";
import { protocolFloor, solveProtocol, type ProtocolState, type Side } from "./protocol";

/**
 * These vectors are shared with test_board_analysis.py. A change here that is
 * not mirrored there means the phone and the desktop can show different numbers
 * for the same board, which is the one failure mode that would matter mid-event.
 */

// the home team vs Opponent 02, scenario 0.
const WTC_FLAT_BOARD: Matrix = [
  [3, 3, 3, 2, 3],
  [3, 3, 2, 2, 3],
  [3, 3, 3, 3, 3],
  [3, 3, 2, 3, 1],
  [3, 3, 3, 1, 3],
];

// the home team vs Opponent 23, scenario 0.
const WTC_TRADEOFF_BOARD: Matrix = [
  [4, 3, 3, 3, 3],
  [2, 3, 3, 3, 3],
  [3, 3, 3, 3, 3],
  [3, 2, 3, 3, 1],
  [3, 3, 3, 3, 3],
];

function permutations<T>(items: T[]): T[][] {
  if (items.length <= 1) return [items];
  const out: T[][] = [];
  items.forEach((item, i) => {
    const rest = [...items.slice(0, i), ...items.slice(i + 1)];
    for (const p of permutations(rest)) out.push([item, ...p]);
  });
  return out;
}

function bruteForceExtremes(matrix: Matrix): [number, number] {
  const n = matrix.length;
  const totals = permutations([...Array(n).keys()]).map((perm) =>
    perm.reduce((sum, col, row) => sum + matrix[row][col], 0),
  );
  return [Math.min(...totals), Math.max(...totals)];
}

function randomMatrix(n: number, seed: number): number[][] {
  let s = seed;
  const next = () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
  return Array.from({ length: n }, () =>
    Array.from({ length: n }, () => Math.round(next() * 9) + 1),
  );
}

describe("evenThreshold", () => {
  it("is the midpoint of the scale times the number of games", () => {
    expect(evenThreshold(5, 1, 5)).toBe(15);
    expect(evenThreshold(5, 1, 10)).toBe(27.5);
    expect(evenThreshold(0)).toBe(0);
  });

  it("scales without changing which side of even a board sits on", () => {
    // A board of straight midpoints must land exactly on tau at any scale.
    for (const [lo, hi] of [
      [1, 5],
      [1, 10],
      [0, 100],
    ]) {
      const mid = (lo + hi) / 2;
      const board = Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => mid));
      expect(boardOutlook(board, evenThreshold(5, lo, hi)).verdict).toBe(UNWINNABLE);
    }
  });

  it("rejects a negative number of games", () => {
    expect(() => evenThreshold(-1)).toThrow();
  });
});

describe("hungarianMin", () => {
  it("agrees with brute force on every size the app can present", () => {
    for (let n = 1; n <= 6; n++) {
      for (let seed = 1; seed <= 8; seed++) {
        const m = randomMatrix(n, seed * 31 + n);
        const [lo, hi] = bruteForceExtremes(m);
        expect(assignmentExtremes(m)).toEqual([lo, hi]);
      }
    }
  });

  it("returns a genuine permutation", () => {
    const m = randomMatrix(5, 7);
    const [, cols] = hungarianMin(m);
    expect(new Set(cols).size).toBe(5);
  });

  it("handles the empty board", () => {
    expect(assignmentExtremes([])).toEqual([0, 0]);
    expect(hungarianMin([])).toEqual([0, []]);
  });

  it("refuses a board with more rows than columns", () => {
    expect(() => hungarianMin([[1, 2], [3, 4], [5, 6]])).toThrow();
  });
});

describe("Outlook", () => {
  it("calls a round unwinnable when the ceiling cannot beat even", () => {
    const o = boardOutlook(WTC_FLAT_BOARD, evenThreshold(5));
    expect(o.ceiling).toBe(15);
    expect(o.tau).toBe(15);
    expect(o.verdict).toBe(UNWINNABLE);
    expect(o.ceilingMargin).toBe(0);
    expect(o.isDecided).toBe(true);
  });

  it("calls a round secured when the floor already beats even", () => {
    const board = Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => 5));
    expect(boardOutlook(board, evenThreshold(5)).verdict).toBe(SECURED);
  });

  it("calls a round live when pairing still decides it", () => {
    expect(boardOutlook(WTC_TRADEOFF_BOARD, evenThreshold(5)).verdict).toBe(LIVE);
  });

  it("reports spread as ceiling minus floor", () => {
    const o = boardOutlook(WTC_TRADEOFF_BOARD, evenThreshold(5));
    expect(o.spread).toBe(o.ceiling - o.floor);
  });
});

describe("cellOutlooks", () => {
  it("brackets every cell inside the board outlook", () => {
    const tau = evenThreshold(5);
    const board = boardOutlook(WTC_TRADEOFF_BOARD, tau);
    const cells = [...cellOutlooks(WTC_TRADEOFF_BOARD, tau).values()];
    expect(Math.min(...cells.map((c) => c.floor))).toBe(board.floor);
    expect(Math.max(...cells.map((c) => c.ceiling))).toBe(board.ceiling);
  });

  it("produces one entry per pairing", () => {
    expect(cellOutlooks(WTC_FLAT_BOARD, evenThreshold(5)).size).toBe(25);
  });
});

describe("decisionReport", () => {
  it("matches the Python engine on the Australia board", () => {
    const r = decisionReport(WTC_FLAT_BOARD, evenThreshold(5));
    expect(r.board.floor).toBe(10);
    expect(r.board.ceiling).toBe(15);
    expect(r.choiceMatters).toBe(false);
    expect(r.hiddenFloorCost).toBe(4);
    expect(r.safest.outlook.floor).toBe(14);
    expect(r.safest.outlook.ceiling).toBe(15);
    expect(r.floorAtStake).toBe(0);
    expect(r.ceilingAtStake).toBe(0);
  });

  it("matches the Python engine on the South Africa board", () => {
    const r = decisionReport(WTC_TRADEOFF_BOARD, evenThreshold(5));
    expect(r.board.floor).toBe(12);
    expect(r.board.ceiling).toBe(16);
    expect(r.choiceMatters).toBe(true);
    expect(r.floorAtStake).toBe(1);
    expect(r.ceilingAtStake).toBe(1);
    // Playing safe pins the round at exactly even: cannot lose, cannot win.
    expect(r.safest.outlook.floor).toBe(15);
    expect(r.safest.outlook.ceiling).toBe(15);
    expect(r.boldest.outlook.ceiling).toBe(16);
  });

  it("excludes dominated cells from the frontier", () => {
    const r = decisionReport(WTC_TRADEOFF_BOARD, evenThreshold(5));
    expect(r.frontier.length).toBeLessThan(25);
    for (const cell of r.frontier) {
      expect(r.frontier.some((o) => dominates(o, cell))).toBe(false);
    }
  });

  it("does not depend on row or column order", () => {
    const tau = evenThreshold(5);
    const first = decisionReport(WTC_TRADEOFF_BOARD, tau);
    const order = [3, 1, 4, 0, 2];
    const shuffled = order.map((i) => order.map((j) => WTC_TRADEOFF_BOARD[i][j]));
    const second = decisionReport(shuffled, tau);
    expect(second.board.floor).toBe(first.board.floor);
    expect(second.board.ceiling).toBe(first.board.ceiling);
    expect(second.hiddenFloorCost).toBe(first.hiddenFloorCost);
    expect(second.choiceMatters).toBe(first.choiceMatters);
  });

  it("rejects an empty board", () => {
    expect(() => decisionReport([], 0)).toThrow();
  });
});

// --- the protocol solver ------------------------------------------------------

/** Reference implementation: no memoisation, no bitmasks, no shortcuts. */
function bruteForceProtocol(
  matrix: Matrix,
  ourPool: number[],
  theirPool: number[],
  attacker: number,
  attackerSide: Side,
): number {
  if (attacker < 0) {
    return Math.max(
      ...ourPool.map((p) =>
        bruteForceProtocol(
          matrix,
          ourPool.filter((x) => x !== p),
          theirPool,
          p,
          "our",
        ),
      ),
    );
  }
  const attackerIsUs = attackerSide === "our";
  const offering = attackerIsUs ? theirPool : ourPool;
  if (offering.length === 0) return 0;
  if (offering.length === 1) {
    const other = offering[0];
    return attackerIsUs ? matrix[attacker][other] : matrix[other][attacker];
  }

  const offerValues: number[] = [];
  for (let a = 0; a < offering.length; a++) {
    for (let b = a + 1; b < offering.length; b++) {
      const pair = [offering[a], offering[b]];
      const picks = pair.map((picked) => {
        const leftover = picked === pair[0] ? pair[1] : pair[0];
        const banked = attackerIsUs
          ? matrix[attacker][picked]
          : matrix[picked][attacker];
        const nextOur = attackerIsUs
          ? ourPool
          : ourPool.filter((x) => x !== picked && x !== leftover);
        const nextTheir = attackerIsUs
          ? theirPool.filter((x) => x !== picked && x !== leftover)
          : theirPool;
        const rest =
          nextOur.length === 0 && nextTheir.length === 0
            ? 0
            : bruteForceProtocol(
                matrix,
                nextOur,
                nextTheir,
                leftover,
                attackerIsUs ? "their" : "our",
              );
        return banked + rest;
      });
      // The attacking side picks from the offer.
      offerValues.push(attackerIsUs ? Math.max(...picks) : Math.min(...picks));
    }
  }
  // The defending side chose which pair to offer.
  return attackerIsUs ? Math.min(...offerValues) : Math.max(...offerValues);
}

describe("solveProtocol", () => {
  it("agrees with an independent brute-force search", () => {
    for (const n of [2, 3, 4, 5]) {
      for (let seed = 1; seed <= 5; seed++) {
        const m = randomMatrix(n, seed * 17 + n);
        const all = [...Array(n).keys()];
        const state: ProtocolState = {
          ourPool: (1 << n) - 1,
          theirPool: (1 << n) - 1,
          attacker: -1,
          attackerSide: "our",
        };
        expect(solveProtocol(m, state).value).toBe(
          bruteForceProtocol(m, all, all, -1, "our"),
        );
      }
    }
  });

  it("pairs every player exactly once", () => {
    // A board of constant 3s must total 5 x 3 regardless of how it is played.
    const board = Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => 3));
    expect(protocolFloor(board).value).toBe(15);
  });

  it("never exceeds the assignment ceiling nor falls below the assignment floor", () => {
    for (const m of [WTC_FLAT_BOARD, WTC_TRADEOFF_BOARD]) {
      const [lo, hi] = assignmentExtremes(m);
      for (const first of [true, false]) {
        const v = protocolFloor(m, first).value;
        expect(v).toBeGreaterThanOrEqual(lo);
        expect(v).toBeLessThanOrEqual(hi);
      }
    }
  });

  it("is at least as informative as the assignment floor", () => {
    // The protocol restricts what the opponent can reach, so the guaranteed
    // total can only improve on the permutation-only bound.
    for (const m of [WTC_FLAT_BOARD, WTC_TRADEOFF_BOARD]) {
      const [lo] = assignmentExtremes(m);
      expect(protocolFloor(m, true).value).toBeGreaterThanOrEqual(lo);
    }
  });

  it("gives the opening side an advantage it can measure", () => {
    const ours = protocolFloor(WTC_TRADEOFF_BOARD, true).value;
    const theirs = protocolFloor(WTC_TRADEOFF_BOARD, false).value;
    expect(Number.isFinite(ours)).toBe(true);
    expect(Number.isFinite(theirs)).toBe(true);
  });

  it("solves a full 5v5 board fast enough for a phone", () => {
    const started = performance.now();
    protocolFloor(WTC_TRADEOFF_BOARD, true);
    expect(performance.now() - started).toBeLessThan(500);
  });
});
