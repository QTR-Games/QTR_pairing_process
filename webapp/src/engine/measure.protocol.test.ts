/**
 * Measurement, not a test assertion: how much does modelling the actual
 * pairing protocol change what we can guarantee, versus the permutation-only
 * assignment bound?
 *
 * Run with:  npx vitest run src/engine/measure.protocol.ts --reporter=basic
 */
import { describe, it } from "vitest";
import boards from "./__fixtures__/wtc2024Boards.json";
import { assignmentExtremes, evenThreshold } from "./boardAnalysis";
import { protocolFloor } from "./protocol";

const TAU = evenThreshold(5, 1, 5);

// Reporting harness, not a regression test. Enable with QTR_MEASURE=1.
describe.skipIf(!process.env.QTR_MEASURE)(
  "protocol vs assignment bound on 31 real boards",
  () => {
  it("measures the gap", () => {
    const rows: {
      opponent: string;
      aFloor: number;
      pFloorUs: number;
      pFloorThem: number;
      ceiling: number;
      initiative: number;
    }[] = [];

    for (const b of boards) {
      const [aFloor, ceiling] = assignmentExtremes(b.matrix);
      const pUs = protocolFloor(b.matrix, true).value;
      const pThem = protocolFloor(b.matrix, false).value;
      rows.push({
        opponent: b.opponent,
        aFloor,
        pFloorUs: pUs,
        pFloorThem: pThem,
        ceiling,
        initiative: pUs - pThem,
      });
    }

    const w = (s: string, n: number) => s.padEnd(n).slice(0, n);
    const f = (x: number, n = 7) => x.toFixed(1).padStart(n);

    console.log("\n" + "=".repeat(96));
    console.log("WHAT THE PROTOCOL GUARANTEES vs WHAT THE ASSIGNMENT BOUND ASSUMES");
    console.log("=".repeat(96));
    console.log(
      w("opponent", 32) +
        "assign".padStart(8) +
        "we open".padStart(9) +
        "they open".padStart(11) +
        "ceiling".padStart(9) +
        "initiat".padStart(9),
    );
    for (const r of [...rows].sort((a, b) => b.initiative - a.initiative)) {
      console.log(
        w(r.opponent, 32) +
          f(r.aFloor, 8) +
          f(r.pFloorUs, 9) +
          f(r.pFloorThem, 11) +
          f(r.ceiling, 9) +
          f(r.initiative, 9),
      );
    }

    const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
    const gainUs = rows.map((r) => r.pFloorUs - r.aFloor);
    const gainThem = rows.map((r) => r.pFloorThem - r.aFloor);
    const init = rows.map((r) => r.initiative);

    console.log("\n" + "-".repeat(96));
    console.log(
      `  protocol floor above assignment floor, we open : mean ${mean(gainUs).toFixed(2)}` +
        `  min ${Math.min(...gainUs).toFixed(1)}  max ${Math.max(...gainUs).toFixed(1)}`,
    );
    console.log(
      `  protocol floor above assignment floor, they open: mean ${mean(gainThem).toFixed(2)}` +
        `  min ${Math.min(...gainThem).toFixed(1)}  max ${Math.max(...gainThem).toFixed(1)}`,
    );
    console.log(
      `  value of the initiative (we open - they open)   : mean ${mean(init).toFixed(2)}` +
        `  min ${Math.min(...init).toFixed(1)}  max ${Math.max(...init).toFixed(1)}`,
    );

    const winUs = rows.filter((r) => r.pFloorUs > TAU).length;
    const winThem = rows.filter((r) => r.pFloorThem > TAU).length;
    const lossUs = rows.filter((r) => r.ceiling <= TAU).length;
    console.log(
      `\n  rounds we can GUARANTEE winning when we open   : ${winUs}/${rows.length}`,
    );
    console.log(
      `  rounds we can GUARANTEE winning when they open : ${winThem}/${rows.length}`,
    );
    console.log(`  rounds unwinnable regardless (ceiling <= tau)   : ${lossUs}/${rows.length}`);

    const aus = rows.find((r) => r.opponent.includes("Thorny"))!;
    console.log(
      `\n  Opponent 02: assignment floor ${aus.aFloor.toFixed(1)}, ` +
        `protocol floor ${aus.pFloorUs.toFixed(1)} (we open) / ` +
        `${aus.pFloorThem.toFixed(1)} (they open), ceiling ${aus.ceiling.toFixed(1)}, tau ${TAU}`,
    );
    });
  },
);
