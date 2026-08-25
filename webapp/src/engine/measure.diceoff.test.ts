/*
  What does it cost to price the dice-off in probability, and how often does
  it have something to say?

  `Verdict` already shows "Going first costs N" in points, gated on the points
  gap being non-zero. That gate hides the more interesting half: on the boards
  where the gap is zero, the roll is genuinely free, and nothing says so.

  Two questions before wiring a percentage into the phone:

    1. cost. `protocolFloor` is cheap and already runs twice per render.
       `winChanceFloor` is the probability solver and its cost is unmeasured
       at this call site. The dodge price is ~293 ms and had to be put behind
       a setting; if this lands anywhere near that, it needs the same
       treatment rather than an always-on slot.

    2. agreement. The points gap and the probability gap are different
       currencies. If they ever disagree about *whether* the roll matters,
       a single sentence cannot speak for both.

  Run with:  $env:QTR_MEASURE=1; npx vitest run src/engine/measure.diceoff.test.ts --disable-console-intercept
*/
import { describe, it } from "vitest";
import { protocolFloor } from "./protocol";
import { winChanceFloor } from "./avoidance";
import boards from "./__fixtures__/wtc2024Boards.json";
import type { Matrix } from "./boardAnalysis";

interface Fixture {
  matrix: number[][];
}

describe.skipIf(!process.env.QTR_MEASURE)("dice-off pricing", () => {
  it("measures cost and signal across the saved boards", () => {
    const boardList = (boards as Fixture[]).map((b) => b.matrix as Matrix).filter((m) => m.length === 5);

    // Warm the JIT so the first board does not carry compilation cost.
    for (const m of boardList.slice(0, 3)) {
      winChanceFloor(m, 1, 5, true);
      winChanceFloor(m, 1, 5, false);
    }

    let ptsMattered = 0;
    let chanceMattered = 0;
    let disagree = 0;
    let worst = 0;
    let total = 0;
    const gaps: number[] = [];
    const ptGaps: number[] = [];

    for (const m of boardList) {
      const t0 = performance.now();
      const cOpen = winChanceFloor(m, 1, 5, true);
      const cRecv = winChanceFloor(m, 1, 5, false);
      const dt = performance.now() - t0;
      total += dt;
      worst = Math.max(worst, dt);

      const pOpen = protocolFloor(m, true).value;
      const pRecv = protocolFloor(m, false).value;

      const pGap = Math.abs(pOpen - pRecv);
      const cGap = Math.abs(cOpen - cRecv);

      if (pGap > 1e-9) ptsMattered++;
      if (cGap > 1e-9) chanceMattered++;
      if (pGap > 1e-9 !== cGap > 1e-9) disagree++;
      if (cGap > 1e-9) gaps.push(cGap * 100);
      if (pGap > 1e-9) ptGaps.push(pGap);
    }

    const n = boardList.length;
    gaps.sort((a, b) => a - b);
    const mean = gaps.reduce((a, b) => a + b, 0) / (gaps.length || 1);
    const distinct = [...new Set(gaps.map((g) => g.toFixed(9)))];

    console.log(`
  boards                              ${n}

  cost of both winChanceFloor calls
    mean per board                    ${(total / n).toFixed(2)} ms
    worst board                       ${worst.toFixed(2)} ms

  how often the roll matters
    in points                         ${ptsMattered}/${n}
    in probability                    ${chanceMattered}/${n}
    currencies disagree               ${disagree}/${n}

  size of the probability gap, when non-zero
    mean                              ${mean.toFixed(1)} pp
    min                               ${(gaps[0] ?? 0).toFixed(1)} pp
    max                               ${(gaps[gaps.length - 1] ?? 0).toFixed(1)} pp
    distinct values                   ${distinct.length}
    they are                          ${distinct.join(", ")}

  size of the POINTS gap, when non-zero
    distinct values                   ${[...new Set(ptGaps.map((g) => g.toFixed(9)))].length}
    they are                          ${[...new Set(ptGaps.map((g) => g.toFixed(9)))].join(", ")}
    they are                          ${distinct.join(", ")}
`);
  }, 120_000);
});
