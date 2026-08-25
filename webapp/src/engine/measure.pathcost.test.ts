/*
  Where does the time actually go?

  Every measurement so far has priced ONE function in isolation, which answers
  "is this feature affordable" but never "what is this screen spending its time
  on". Only the second question can tell us what to fix.

  measure.rendercost covers the LivePanel path. This covers the other two:

    phone   (Verdict.tsx)    protocolFloor x2, decisionReport, outlook,
                             reachReport. worstMatchupDodge is NOT counted --
                             it is gated behind `asked`, so in "off" and
                             "onDemand" the engine is not run at all.
    desktop (Currencies + DesktopWorkspace + ReachPanel)
                             all of the above, plus winChanceFloor x2,
                             cellOutlooks, dodgeMapChance, openingChoice.

  The prior going in: winChanceFloor measured 17-36 ms during the reach work
  and Currencies.tsx:45-52 calls it TWICE. Worse, reading avoidance.ts, all
  three of winChanceFloor(open), winChanceFloor(receive) and dodgeMapChance
  rebuild `probabilityMatrix` from the same board, and both winChanceFloor and
  dodgeMapChance compute the same unconstrained baseline -- so the desktop
  builds the same probability grid three times and the same baseline three
  times per render.

  If that is where the time is, the answer to "can the maths be faster" is not
  "rewrite the solver". It is "stop paying three times for one answer".

  Method: five runs per board per call, keep the MIN (least contaminated by GC
  and JIT warm-up), report the mean of those minima across the 31 real boards
  plus the worst single board. Everything warmed once before timing.

  Run with:
    $env:QTR_MEASURE=1; npx vitest run src/engine/measure.pathcost.test.ts --disable-console-intercept
*/
import { describe, it } from "vitest";
import { dodgeMapChance, winChanceFloor, worstMatchupDodge } from "./avoidance";
import { cellOutlooks, decisionReport, evenThreshold, type Matrix } from "./boardAnalysis";
import { outlook } from "./opponent";
import { openingChoice, protocolFloor } from "./protocol";
import { reachReport } from "./reach";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];
const RUNS = 5;

/** Min of RUNS timings in ms. Min, because we want the floor and not the noise. */
function best(fn: () => unknown): number {
  let min = Infinity;
  for (let r = 0; r < RUNS; r++) {
    const t = performance.now();
    fn();
    const dt = performance.now() - t;
    if (dt < min) min = dt;
  }
  return min;
}

interface Call {
  name: string;
  /** "phone" calls also run on desktop; "desktop" calls run only there. */
  path: "phone" | "desktop";
  gated?: boolean;
  run: (m: Matrix, tau: number) => unknown;
}

const CALLS: Call[] = [
  { name: "protocolFloor(open)", path: "phone", run: (m) => protocolFloor(m, true) },
  { name: "protocolFloor(receive)", path: "phone", run: (m) => protocolFloor(m, false) },
  { name: "decisionReport", path: "phone", run: (m, tau) => decisionReport(m, tau) },
  {
    name: "outlook",
    path: "phone",
    // Mirrors Verdict.tsx:69-79 exactly. The JointState shape matters: there is
    // no `ourTeamFirst` field, and inventing one silently yields NaN.
    run: (m) =>
      outlook(
        m,
        {
          ourPool: (1 << m.length) - 1,
          theirPool: (1 << m.length) - 1,
          attacker: -1,
          attackerSide: "our",
        },
        protocolFloor(m, true).value,
      ),
  },
  { name: "reachReport", path: "phone", run: (m) => reachReport(m) },

  { name: "winChanceFloor(open)", path: "desktop", run: (m) => winChanceFloor(m, 1, 5, true) },
  { name: "winChanceFloor(receive)", path: "desktop", run: (m) => winChanceFloor(m, 1, 5, false) },
  { name: "dodgeMapChance", path: "desktop", run: (m) => dodgeMapChance(m, 1, 5) },
  { name: "cellOutlooks", path: "desktop", run: (m, tau) => cellOutlooks(m, tau) },
  { name: "openingChoice", path: "desktop", run: (m) => openingChoice(m) },

  // Not in either default path. Measured anyway so the gate can be defended
  // with a number instead of an assumption.
  { name: "worstMatchupDodge", path: "desktop", gated: true, run: (m) => worstMatchupDodge(m, 1, 5) },
];

describe.skipIf(!process.env.QTR_MEASURE)("engine render-path profile", () => {
  // 31 boards x 11 calls x 5 runs, and the slowest call is ~174 ms on its own.
  it("ranks every engine call the two screens make on a real board", { timeout: 600_000 }, () => {
    for (const c of CALLS) {
      const m = FIXTURES[0].matrix;
      c.run(m, evenThreshold(m.length, 1, 5));
    }

    const samples = new Map<string, number[]>(CALLS.map((c) => [c.name, []]));

    for (const f of FIXTURES) {
      const tau = evenThreshold(f.matrix.length, 1, 5);
      for (const c of CALLS) {
        samples.get(c.name)!.push(best(() => c.run(f.matrix, tau)));
      }
    }

    const rows = CALLS.map((c) => {
      const xs = samples.get(c.name)!;
      return {
        name: c.name,
        path: c.path,
        gated: c.gated === true,
        mean: xs.reduce((a, b) => a + b, 0) / xs.length,
        worst: Math.max(...xs),
      };
    }).sort((a, b) => b.mean - a.mean);

    console.log(`\n  boards: ${FIXTURES.length}   runs per board: ${RUNS} (min kept)\n`);
    console.log("  RANKED BY MEAN COST PER CALL");
    console.log("  " + "-".repeat(72));
    for (const r of rows) {
      console.log(
        `  ${(r.name + (r.gated ? " [gated]" : "")).padEnd(30)}${r.path.padEnd(9)}` +
          `mean ${r.mean.toFixed(3).padStart(9)} ms   worst ${r.worst.toFixed(3).padStart(9)} ms`,
      );
    }

    const live = rows.filter((r) => !r.gated);
    const phone = live.filter((r) => r.path === "phone").reduce((a, b) => a + b.mean, 0);
    const desktop = live.reduce((a, b) => a + b.mean, 0);

    console.log("  " + "-".repeat(72));
    console.log(`  phone render path total    ${phone.toFixed(3)} ms`);
    console.log(`  desktop render path total  ${desktop.toFixed(3)} ms`);

    const top = live[0];
    console.log(
      `\n  biggest single call: ${top.name} at ${top.mean.toFixed(3)} ms ` +
        `(${((top.mean / desktop) * 100).toFixed(1)}% of the desktop path)`,
    );

    const chance = live.filter(
      (r) => r.name.startsWith("winChanceFloor") || r.name === "dodgeMapChance",
    );
    const chanceTotal = chance.reduce((a, b) => a + b.mean, 0);
    console.log(
      `  probability family:  ${chanceTotal.toFixed(3)} ms ` +
        `(${((chanceTotal / desktop) * 100).toFixed(1)}% of the desktop path) ` +
        `across ${chance.length} calls that each rebuild probabilityMatrix`,
    );
    console.log(
      `  everything else:     ${(desktop - chanceTotal).toFixed(3)} ms ` +
        `(${(((desktop - chanceTotal) / desktop) * 100).toFixed(1)}%)\n`,
    );
  });
});
