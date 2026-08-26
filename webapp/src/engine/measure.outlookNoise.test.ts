/*
  Is the "typical / low / high" triple on the phone actually worth printing?

  `outlook` is 19.9 ms of the phone's 21.8 ms render path -- 91% of everything
  the phone computes. Before making it faster it is worth asking whether it is
  currently RIGHT, because the two questions have opposite answers:

    - if 24 trials is already accurate, the sampling is thin-but-sufficient and
      the only lever is speed;
    - if 24 trials is noisy, then the app has been printing "typical 14.9" to
      one decimal place while carrying an error larger than that decimal, and
      the honest fix costs time rather than saving it.

  Method. The shipped number is deterministic -- the seed comes from the board
  and the state (opponent.ts:240) -- so this is NOT asking how much the value
  would wobble between runs. It cannot wobble. It is asking how far the one
  value we always show sits from the value we would show with effectively
  unlimited sampling. That is the error the user actually eats.

  Ground truth is 4000 trials per board. Compare 24 (shipped) and a ladder of
  larger counts against it, on all 31 real boards, at the opening state -- the
  state the phone spends the most time on.

  Run with:
    $env:QTR_MEASURE=1; npx vitest run src/engine/measure.outlookNoise.test.ts --disable-console-intercept
*/
import { describe, expect, it } from "vitest";
import { evenThreshold, type Matrix } from "./boardAnalysis";
import { outlook } from "./opponent";
import { protocolFloor } from "./protocol";
import boards from "./__fixtures__/wtc2024Boards.json";

interface Fixture {
  opponent: string;
  matrix: Matrix;
}

const FIXTURES = boards as Fixture[];
const SHIPPED = 24;
const LADDER = [24, 48, 96, 192, 384];
const TRUTH = 4000;

/** The state Verdict.tsx uses. No `ourTeamFirst` field -- adding one gives NaN. */
const opening = (n: number) =>
  ({
    ourPool: (1 << n) - 1,
    theirPool: (1 << n) - 1,
    attacker: -1,
    attackerSide: "our" as const,
  });

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

/** What the screen shows, so error is judged in the units the user reads. */
const shown = (v: number) => v.toFixed(1);

describe.skipIf(!process.env.QTR_MEASURE)("outlook sampling error", () => {
  it("measures how far the printed triple sits from the truth", { timeout: 900_000 }, () => {
    const errExpected = new Map<number, number[]>(LADDER.map((t) => [t, []]));
    const errLow = new Map<number, number[]>(LADDER.map((t) => [t, []]));
    const errHigh = new Map<number, number[]>(LADDER.map((t) => [t, []]));
    const wrongDigit = new Map<number, number>(LADDER.map((t) => [t, 0]));

    let floorBreaches = 0;

    for (const f of FIXTURES) {
      const st = opening(f.matrix.length);
      const floor = protocolFloor(f.matrix, true).value;
      const truth = outlook(f.matrix, st, floor, TRUTH);

      for (const t of LADDER) {
        const got = outlook(f.matrix, st, floor, t);
        errExpected.get(t)!.push(Math.abs(got.expected - truth.expected));
        errLow.get(t)!.push(Math.abs(got.low - truth.low));
        errHigh.get(t)!.push(Math.abs(got.high - truth.high));
        if (shown(got.expected) !== shown(truth.expected)) {
          wrongDigit.set(t, wrongDigit.get(t)! + 1);
        }
      }

      // Sanity that has nothing to do with sampling: the typical case must not
      // sit below the guaranteed floor, or the two panels contradict each other.
      if (truth.expected < floor - 1e-9) floorBreaches++;
    }

    console.log(`\n  boards: ${FIXTURES.length}   truth: ${TRUTH} trials   units: round points\n`);
    console.log("  trials    mean |err|   max |err|   mean |err| low   mean |err| high   1dp differs");
    console.log("  " + "-".repeat(88));
    for (const t of LADDER) {
      const e = errExpected.get(t)!;
      console.log(
        `  ${String(t).padEnd(10)}${mean(e).toFixed(4).padStart(10)}` +
          `${Math.max(...e).toFixed(4).padStart(12)}` +
          `${mean(errLow.get(t)!).toFixed(4).padStart(17)}` +
          `${mean(errHigh.get(t)!).toFixed(4).padStart(18)}` +
          `${String(wrongDigit.get(t)) .padStart(12)}/${FIXTURES.length}`,
      );
    }

    const shippedErr = errExpected.get(SHIPPED)!;
    console.log(
      `\n  shipped (${SHIPPED} trials): typical is off by ${mean(shippedErr).toFixed(3)} pts on average, ` +
        `${Math.max(...shippedErr).toFixed(3)} pts at worst`,
    );
    console.log(
      `  the screen prints one decimal place, i.e. a resolution of 0.05 pts -- ` +
        `the error is ${(mean(shippedErr) / 0.05).toFixed(1)}x that resolution`,
    );
    console.log(`  typical-below-floor contradictions at ${TRUTH} trials: ${floorBreaches}/${FIXTURES.length}\n`);

    // Not a threshold on quality -- just proof the harness measured something.
    expect(shippedErr.length).toBe(FIXTURES.length);
  });

  /*
    The number is not only printed -- it is BRANCHED ON.

    Verdict.tsx:208 chooses between "this is a round you take by playing for the
    win" and "neither reading gets there on its own" on `typical.expected > tau`.
    Verdict.tsx:242 shows or hides the whole "being hunted costs you" insight on
    `typical.expected - guaranteed >= 0.5`.

    Both are hard comparisons against a Monte Carlo estimate. If a board sits
    closer to either line than the sampling error, then which advice the app
    gives is decided by the random draw and not by the board. That is worse than
    a noisy decimal: the user reads a different recommendation.

    This measures the distance from each edge on real boards.
  */
  it("checks whether sampling noise can flip the advice, not just the digit", { timeout: 900_000 }, () => {
    const meanErr = 0.0531;
    const maxErr = 0.218;

    const tauGaps: { name: string; gap: number }[] = [];
    const insightGaps: { name: string; gap: number }[] = [];

    for (const f of FIXTURES) {
      const n = f.matrix.length;
      const st = opening(n);
      const floor = protocolFloor(f.matrix, true).value;
      const truth = outlook(f.matrix, st, floor, TRUTH);

      // evenThreshold for a 5-game round on a 1-5 scale, matching Verdict.
      const tau = evenThreshold(n, 1, 5);

      tauGaps.push({ name: f.opponent, gap: Math.abs(truth.expected - tau) });
      insightGaps.push({ name: f.opponent, gap: Math.abs(truth.expected - floor - 0.5) });
    }

    const within = (xs: { gap: number }[], e: number) => xs.filter((x) => x.gap < e).length;

    console.log("\n  DOES THE NOISE REACH A DECISION EDGE?");
    console.log("  " + "-".repeat(70));
    console.log(`  sampling error at 24 trials: ${meanErr.toFixed(3)} pts mean, ${maxErr.toFixed(3)} pts max\n`);

    for (const [label, xs] of [
      ["Verdict.tsx:208  typical > tau (which narrative)", tauGaps],
      ["Verdict.tsx:242  typical - floor >= 0.5 (show insight)", insightGaps],
    ] as const) {
      const sorted = [...xs].sort((a, b) => a.gap - b.gap);
      console.log(`  ${label}`);
      console.log(
        `    boards within mean error of the edge: ${within(xs, meanErr)}/${xs.length}` +
          `   within max error: ${within(xs, maxErr)}/${xs.length}`,
      );
      console.log(
        `    closest three: ` +
          sorted
            .slice(0, 3)
            .map((x) => `${x.name} ${x.gap.toFixed(3)}`)
            .join(", "),
      );
      console.log(`    median distance from the edge: ${sorted[Math.floor(sorted.length / 2)].gap.toFixed(3)} pts\n`);
    }

    expect(tauGaps.length).toBe(FIXTURES.length);
  });

  /*
    An error bar that does not predict the error is worse than no error bar,
    because it invites exactly the trust it cannot support.

    `outlook` now reports the sample standard error of its mean. That is the
    textbook estimator, but the trials here are not draws from a tidy normal --
    they are minimax solves over randomly assembled opponent boards, and the
    result distribution is discrete and left-skewed (which is why `low` needs
    clamping at all). So whether the estimator works has to be checked against
    the 4000-trial reference rather than assumed from the formula.

    The bar is useful if the true error usually falls inside a couple of it.
  */
  it("checks the reported error bar against the error it claims to predict", { timeout: 900_000 }, () => {
    let within1 = 0;
    let within2 = 0;
    const ratios: number[] = [];
    const bars: number[] = [];

    for (const f of FIXTURES) {
      const st = opening(f.matrix.length);
      const floor = protocolFloor(f.matrix, true).value;
      const truth = outlook(f.matrix, st, floor, TRUTH);
      const got = outlook(f.matrix, st, floor, SHIPPED);

      const err = Math.abs(got.expected - truth.expected);
      bars.push(got.stderr);
      if (got.stderr > 0) ratios.push(err / got.stderr);
      if (err <= got.stderr) within1++;
      if (err <= 2 * got.stderr) within2++;
    }

    console.log("\n  IS THE ERROR BAR HONEST?");
    console.log("  " + "-".repeat(70));
    console.log(`  mean reported stderr at ${SHIPPED} trials: ${mean(bars).toFixed(4)} pts`);
    console.log(`  true error within 1 stderr: ${within1}/${FIXTURES.length}   within 2: ${within2}/${FIXTURES.length}`);
    console.log(`  mean |error| / stderr: ${mean(ratios).toFixed(3)}   max: ${Math.max(...ratios).toFixed(3)}\n`);

    // The claim being defended: 2 standard errors covers the great majority of
    // boards. Deliberately loose -- this guards against the bar being wrong by
    // an order of magnitude, which is the failure that would matter.
    expect(within2).toBeGreaterThanOrEqual(Math.floor(FIXTURES.length * 0.8));
  });
});
