import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { ARMIES, armyInfo } from "./factions";

/**
 * Reconciliation of our army table against Longshanks' own catalogue.
 *
 * Longshanks ships its catalogue as JSON embedded in every event payload. The
 * fixture beside this file is that table for event 37180, deduped by id -- the
 * payload repeats it verbatim roughly seven times, so a count taken without
 * deduping is multiplied and meaningless.
 *
 * This is the only test here that can detect something *missing*. Every other
 * test asks whether what we carry resolves correctly, which is silent about a
 * record that was never added -- and that silence is what let two entire armies
 * sit absent from this table undetected, because no player at the event brought
 * either one. An attendance-derived check bounds nothing; only the upstream
 * table does.
 *
 * When this fails after a catalogue update, the fix is to reconcile against the
 * refreshed table, not to widen the exceptions below.
 */
const CATALOGUE = new URL("./__fixtures__/longshanks-catalog-37180.csv", import.meta.url);

/**
 * Longshanks models the Unlimited *format* as an army, and each faction's entry
 * in that format as one of its leaders. They are not warcasters, so this table
 * carries the army with an empty roster and deliberately omits the fourteen.
 *
 * Spelled exactly as upstream spells them. "Cygnar  Unlimited" carries a double
 * space, which is upstream's typo and is preserved rather than tidied -- the
 * same reasoning that keeps the "Huxely" misspelling: these strings are join
 * keys against Longshanks, not prose.
 */
const FORMAT_MARKERS_NOT_CARRIED = [
  "Circle Orboros Unlimited",
  "Convergence of Cyriss Unlimited",
  "Crucible Guard Unlimited",
  "Cryx Unlimited",
  "Cygnar  Unlimited",
  "Grymkin Unlimited",
  "Infernals Unlimited",
  "Khador Unlimited",
  "Legion of Everblight Unlimited",
  "Mercenaries Unlimited",
  "Protectorate of Menoth Unlimited",
  "Retribution of Scyrah Unlimited",
  "Skorne Unlimited",
  "Trollbloods Unlimited",
];

interface Row {
  id: string;
  kind: "army" | "leader";
  active: string;
  faction: string;
  name: string;
  parentName: string;
}

function catalogue(): Row[] {
  const text = readFileSync(CATALOGUE, "utf8");
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .slice(1)
    .map((line) => {
      const f = line.split(",");
      return { id: f[0], kind: f[1] as Row["kind"], active: f[2], faction: f[3], name: f[5], parentName: f[7] };
    });
}

const rows = catalogue();
const activeRows = rows.filter((r) => r.active === "1");
const upstreamArmies = activeRows.filter((r) => r.kind === "army");
const upstreamLeaders = activeRows.filter((r) => r.kind === "leader");
const retired = rows.filter((r) => r.active !== "1");

describe("catalogue reconciliation", () => {
  it("reads a deduped fixture", () => {
    expect(rows.length).toBe(246);
    expect(new Set(rows.map((r) => r.id)).size).toBe(246);
    expect(upstreamArmies.length).toBe(42);
    expect(upstreamLeaders.length).toBe(200);
  });

  it("carries every active army, under our name for it", () => {
    const missing = upstreamArmies.filter((r) => !armyInfo(r.name)).map((r) => `${r.id} ${r.name}`);
    expect(missing).toEqual([]);
  });

  it("files every army under the faction upstream gives it", () => {
    const wrong = upstreamArmies
      .filter((r) => armyInfo(r.name) && armyInfo(r.name)!.faction !== r.faction)
      .map((r) => `${r.name}: ours=${armyInfo(r.name)!.faction} upstream=${r.faction}`);
    expect(wrong).toEqual([]);
  });

  it("carries every active leader except the documented format markers", () => {
    const missing = upstreamLeaders
      .filter((r) => !FORMAT_MARKERS_NOT_CARRIED.includes(r.name))
      .filter((r) => {
        const army = armyInfo(r.parentName);
        return !army || !army.leaders.includes(r.name);
      })
      .map((r) => `${r.id} ${r.name} (${r.parentName})`);
    expect(missing).toEqual([]);
  });

  it("omits exactly the fourteen format markers and nothing else", () => {
    const absent = upstreamLeaders
      .filter((r) => {
        const army = armyInfo(r.parentName);
        return !army || !army.leaders.includes(r.name);
      })
      .map((r) => r.name)
      .sort();
    expect(absent).toEqual([...FORMAT_MARKERS_NOT_CARRIED].sort());
  });

  it("invents no leader upstream does not have", () => {
    const upstreamByArmy = new Map<string, Set<string>>();
    for (const r of upstreamLeaders) {
      const army = armyInfo(r.parentName);
      if (!army) continue;
      if (!upstreamByArmy.has(army.army)) upstreamByArmy.set(army.army, new Set());
      upstreamByArmy.get(army.army)!.add(r.name);
    }
    const extra: string[] = [];
    for (const a of ARMIES) {
      for (const leader of a.leaders) {
        if (!upstreamByArmy.get(a.army)?.has(leader)) extra.push(`${a.army}: ${leader}`);
      }
    }
    expect(extra).toEqual([]);
  });

  it("carries none of the retired entries", () => {
    expect(retired.map((r) => `${r.id} ${r.name}`).sort()).toEqual([
      "1235 Aurora 1",
      "1239 Locke",
      "1300 Mortenebra",
      "1394 Asphyxious",
    ]);
    const leaked = retired
      .filter((r) => r.kind === "leader")
      .filter((r) => armyInfo(r.parentName)?.leaders.includes(r.name))
      .map((r) => `${r.id} ${r.name} (${r.parentName})`);
    expect(leaked).toEqual([]);
  });
});
