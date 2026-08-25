/**
 * Step 1 of the WTC pairing protocol: the captains dice off, and the winner
 * CHOOSES whether to be Team A or Team B.
 *
 * Player Pack 2026 v1.1 p.20 / 2025 v1.3 p.22, step 1, verbatim:
 *
 *   "Dice off until one captain has rolled higher than the other. The captain
 *    with the higher roll gets to choose whether they are Team A, or Team B in
 *    the process below."
 *
 * Team B nominates first. In this engine that is `ourTeamFirst = true`.
 *
 * The app already supports both -- it is a dropdown in App.tsx -- but it makes
 * the captain flip it and compare by eye. The engine can answer it outright.
 * This harness asks whether that is worth doing:
 *
 *   1. How often does the choice actually change the guaranteed total?
 *   2. When it does, is opening better or worse -- and is there a rule?
 *   3. Does the answer in points agree with the answer in P(>= 3 wins)?
 *
 * (3) matters most. Winning the roll and choosing the wrong side is a mistake
 * made before a single rating is read, and it is unrecoverable.
 *
 * Run with:
 *   $env:QTR_MEASURE=1; npx vitest run src/engine/measure.openOrReceive.test.ts
 */
import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { protocolFloor } from "./protocol";
import { winChanceFloor } from "./avoidance";

const FIXTURES = boards as { opponent: string; matrix: number[][] }[];
const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);

describe.skipIf(!process.env.QTR_MEASURE)("open or receive", () => {
  it("prices the step-1 decision", { timeout: 120_000 }, () => {
    const pad = (s: string, n: number) => s.padEnd(n).slice(0, n);

    console.log("=".repeat(96));
    console.log("STEP 1: WIN THE ROLL -- OPEN OR MAKE THEM OPEN?  " + FIXTURES.length + " boards");
    console.log("=".repeat(96));
    console.log(
      pad("opponent", 26) +
        pad("openPts", 10) +
        pad("recvPts", 10) +
        pad("gainPts", 10) +
        pad("openP", 10) +
        pad("recvP", 10) +
        pad("gainP", 10) +
        pad("agree", 8),
    );
    console.log("-".repeat(96));

    const ptsGains: number[] = [];
    const chanceGains: number[] = [];
    let ptsPrefersOpen = 0;
    let chancePrefersOpen = 0;
    let ptsIndifferent = 0;
    let chanceIndifferent = 0;
    let agree = 0;

    for (const { opponent, matrix } of FIXTURES) {
      const openPts = protocolFloor(matrix, true).value;
      const recvPts = protocolFloor(matrix, false).value;
      const openP = winChanceFloor(matrix, 1, 5, true);
      const recvP = winChanceFloor(matrix, 1, 5, false);

      // Positive gain = the better choice beat the worse one by this much.
      const gainPts = Math.abs(openPts - recvPts);
      const gainP = Math.abs(openP - recvP);
      ptsGains.push(gainPts);
      chanceGains.push(gainP);

      const ptsPick = gainPts < 1e-9 ? "-" : openPts > recvPts ? "open" : "recv";
      const chancePick = gainP < 1e-9 ? "-" : openP > recvP ? "open" : "recv";
      if (ptsPick === "open") ptsPrefersOpen++;
      if (ptsPick === "-") ptsIndifferent++;
      if (chancePick === "open") chancePrefersOpen++;
      if (chancePick === "-") chanceIndifferent++;

      // Do the two currencies pick the same side when both have an opinion?
      const bothDecided = ptsPick !== "-" && chancePick !== "-";
      const same = bothDecided ? ptsPick === chancePick : true;
      if (same) agree++;

      console.log(
        pad(opponent, 26) +
          pad(openPts.toFixed(2), 10) +
          pad(recvPts.toFixed(2), 10) +
          pad(`${ptsPick} ${gainPts.toFixed(2)}`, 10) +
          pad(`${(openP * 100).toFixed(1)}%`, 10) +
          pad(`${(recvP * 100).toFixed(1)}%`, 10) +
          pad(`${chancePick} ${(gainP * 100).toFixed(1)}%`, 10) +
          pad(bothDecided ? (same ? "yes" : "NO") : "n/a", 8),
      );
    }

    console.log("-".repeat(96));
    console.log(`points  : prefers open ${ptsPrefersOpen}/${FIXTURES.length}, indifferent ${ptsIndifferent}`);
    console.log(`chance  : prefers open ${chancePrefersOpen}/${FIXTURES.length}, indifferent ${chanceIndifferent}`);
    console.log(`mean gain from choosing correctly : ${mean(ptsGains).toFixed(3)} pts / ${(mean(chanceGains) * 100).toFixed(2)}%`);
    console.log(`max  gain from choosing correctly : ${Math.max(...ptsGains).toFixed(3)} pts / ${(Math.max(...chanceGains) * 100).toFixed(2)}%`);
    console.log(`two currencies pick the same side : ${agree}/${FIXTURES.length}`);
    console.log("=".repeat(96));
  });
});
