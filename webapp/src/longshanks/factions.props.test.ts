/**
 * Properties of the leader search that hold over the whole army table.
 *
 * The cases in `factions.test.ts` are examples: each one pins an answer someone
 * reasoned about. These are different in kind -- they quantify over every row
 * in `ARMIES` and state a rule that must hold for all of them, so a catalogue
 * change is checked against the rule rather than against whichever leaders
 * happened to have a test written about them.
 *
 * That matters because the catalogue is the thing that moves. The armies added
 * in #147 took the set of leaders whose armyless resolution is ambiguous from
 * six to ten, with every test in the suite green: nothing in the table pinned
 * the set, so growing it was silent. Four existing leaders changed which army
 * they resolve to and nothing said so.
 *
 * Each test here has one job and they do not overlap:
 *
 *   monotonicity   catches an answer that gets worse when the badge gets better
 *   ambiguous set  catches the catalogue growing a new collision
 *   collapsing     catches a new numbered printing arriving unremarked
 */
import { describe, expect, it } from "vitest";
import { ARMIES, findLeader } from "./factions";

/** A leader name without its Longshanks printing number, as the module does it. */
const bare = (leader: string) => leader.replace(/\s+\d+$/, "");

const show = (r: ReturnType<typeof findLeader>) => (r ? `${r.leader} @ ${r.army}` : "undefined");

/** A minimal list naming one model, which is all these properties need. */
const listNaming = (name: string) => `Army List\n[Leader] ${name}\nStormclad 18\n`;

/** Every (army, leader) pair in the table, which is the population under test. */
const rows = ARMIES.flatMap((info) => info.leaders.map((leader) => ({ info, leader })));

describe("findLeader is monotone in the badge", () => {
  /*
    The property: adding a TRUE constraint must never make the answer less
    determinate, and must never change who is named.

    Three ways that can break, named so a failure says which happened:

      LOST   a badge turns a resolved answer into undefined
      IDENT  a badge changes WHICH character is named
      VAGUE  a badge makes a numbered answer revert to the bare form

    Stating it this way buys coverage no example can. It quantifies over all 186
    leader literals and needs no table of expected values to go stale, because
    it compares the resolver against itself rather than against a transcript.

    Measured on the commit this fix lands against: 2 violating rows, both
    "Caine 4" -- unbadged and faction-badged it read Caine @ First Army, while
    its own army badge read Caine 4. A different character depending on how much
    true information you supplied. Nothing else in the table violated it.

    That pre-fix figure is recorded, not asserted, and deliberately so: counted
    over adjacent badge steps it is 2 violations and counted over all three
    pairs it is 4, so the number is meaningless without its method attached. The
    assertion below is zero over all pairs, which is the same answer under every
    counting method and so cannot be misread.

    What it does NOT cover, so it is not over-trusted: a refusal that stays a
    refusal is monotone, so the "Lylyth 1" false refusals never engaged this at
    all and need the explicit matrix in factions.test.ts. Only true badges are
    tested; a wrong badge is a separate question. And it says nothing about
    which of two armies is named, since both name the same character.

    The population was 186 leader literals when this was written, and that is
    deliberately not asserted. Pinning it would fail on any benign addition to
    the catalogue, for a reason having nothing to do with monotonicity -- which
    is exactly the staleness a property test exists to avoid. The floor below
    only guards against the property passing vacuously over an empty table; the
    ambiguous-set guard owns the job of noticing the catalogue moved.
  */
  it("never answers worse for being told more", () => {
    const violations: string[] = [];

    for (const { info, leader } of rows) {
      const list = listNaming(leader);
      const steps: [string, ReturnType<typeof findLeader>][] = [
        ["no badge", findLeader(list)],
        ["faction", findLeader(list, info.faction)],
        ["army", findLeader(list, info.army)],
      ];

      for (let i = 0; i < steps.length; i++) {
        for (let j = i + 1; j < steps.length; j++) {
          const [loose, a] = steps[i];
          const [tight, b] = steps[j];
          const where = `${leader} (${info.army}): ${loose}=${show(a)} ${tight}=${show(b)}`;

          if (a && !b) violations.push(`LOST  ${where}`);
          if (!a || !b || a.leader === b.leader) continue;
          const reverted =
            bare(a.leader) === bare(b.leader) &&
            a.leader !== bare(a.leader) &&
            b.leader === bare(b.leader);
          violations.push(`${reverted ? "VAGUE" : "IDENT"} ${where}`);
        }
      }
    }

    expect(rows.length, "property ran over an empty table").toBeGreaterThan(100);
    expect(violations, `badge made the answer worse:\n  ${violations.join("\n  ")}`).toEqual([]);
  });
});

describe("the leaders a list cannot settle without a badge", () => {
  /*
    Which armies could hold a leader, once the printing number is collapsed
    away. This is the grouping the matcher actually uses -- `needles` searches
    for the bare name -- so it is the grouping the ambiguity has to be measured
    on. Grouping on exact literals instead gives the same within-faction count
    with a different member ("caine 4" in place of "caine") and loses "lylyth"
    from the cross-faction set entirely. Two methods agreeing on a count is
    evidence they measured the same field, not that either number is right.
  */
  const armiesByStem = new Map<string, string[]>();
  for (const { info, leader } of rows) {
    const stem = bare(leader).toLowerCase();
    armiesByStem.set(stem, [...(armiesByStem.get(stem) ?? []), info.army]);
  }

  const ambiguous = [...armiesByStem].filter(([, armies]) => new Set(armies).size > 1);
  const factionsOf = (armies: string[]) =>
    new Set(armies.map((n) => ARMIES.find((a) => a.army === n)!.faction));

  const within = ambiguous.filter(([, armies]) => factionsOf(armies).size === 1);
  const across = ambiguous.filter(([, armies]) => factionsOf(armies).size > 1);

  /** Names the armies in the failure, so it carries its own diagnosis. */
  const describeSet = (set: [string, string[]][]) =>
    set.map(([stem, armies]) => `${stem} [${[...new Set(armies)].sort().join(", ")}]`).sort();

  const pin = (label: string, set: [string, string[]][], expected: string[]) => {
    const got = set.map(([stem]) => stem).sort();
    const added = describeSet(set.filter(([s]) => !expected.includes(s)));
    const gone = expected.filter((s) => !got.includes(s));
    const why = [
      added.length ? `newly ambiguous: ${added.join("; ")}` : "",
      gone.length ? `no longer ambiguous: ${gone.join(", ")}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    expect(got, `${label} changed -- ${why}`).toEqual([...expected].sort());
  };

  it("pins the leaders two armies of one faction share", () => {
    // Ten leaders whose army is decided by array order when no badge narrows
    // it. The character named is right; the army is pool[0]'s. That is the
    // open problem this guard does NOT fix -- it needs a way to say "army
    // uncertain" that the return type has no room for -- so the set is pinned
    // instead, to make growing it loud.
    pin("within-faction ambiguous set", within, [
      "aiakos",
      "bagadibawm",
      "caine",
      "feora",
      "jakes",
      "kovoskiy",
      "malekus",
      "sorscha",
      "sparkhammer",
      "thyra",
    ]);
  });

  it("pins the leaders whose name spans two factions", () => {
    // Here the table genuinely cannot say what the repetition means: Khador's
    // Butcher is not Orgoth's, but Cryx's Rahera and the Talion Charter's are
    // one character in two factions, and nothing in these rows separates the
    // two situations.
    pin("cross-faction ambiguous set", across, [
      "butcher",
      "gunnbjorn",
      "khythos",
      "lylyth",
      "rahera",
    ]);
  });

  it("resolves a cross-faction name only where one army prints it bare", () => {
    /*
      Stated as a rule rather than a list of expected answers, so the deliberate
      cost of matching literals first falls out of it instead of sitting beside
      it as an exception.

      The rule: a name shared across factions resolves only if exactly one army
      carries it as a literal row. Then the list said that row's name exactly
      and is taken at its word. Otherwise two factions answer equally well and
      the refusal stands.

      Four of the five refuse, because both their armies print the bare name.
      "lylyth" is the one that resolves -- only Shadowflame Shard has a bare
      "Lylyth" row, Legion having numbered theirs -- and that is the cost
      recorded in factions.test.ts, derived here rather than asserted.
    */
    for (const [stem, armies] of across) {
      const bareRows = [...new Set(armies)].filter((army) =>
        ARMIES.find((a) => a.army === army)!.leaders.some((l) => l.toLowerCase() === stem),
      );
      const answer = findLeader(listNaming(stem));
      const why = `${stem} is printed bare by [${bareRows.join(", ")}] but answered ${show(answer)}`;

      if (bareRows.length === 1) {
        expect(answer, why).toEqual({ leader: expect.any(String), army: bareRows[0] });
        expect(bare(answer!.leader).toLowerCase(), why).toBe(stem);
      } else {
        expect(answer, why).toBeUndefined();
      }
    }
  });
});

describe("the printings that collapse", () => {
  /*
    Three different populations, pinned separately because conflating them is
    how the membership rule for TITLES went stale. In increasing severity:

      collapse occurs           a literal differs from its bare form
      collapse has a rival      the stem has more than one literal
      collapse substitutes      the bare form is itself a row in the table

    Only the third can name the wrong character, and only the second can even
    reach the question. "Aurora 2" sits in the first and nowhere else, which is
    exactly what makes it the control: it proves collapsing is not the defect,
    because it collapses and still resolves correctly. A control that did not
    collapse would prove nothing.
  */
  const literalsByStem = new Map<string, Set<string>>();
  for (const { leader } of rows) {
    const stem = bare(leader).toLowerCase();
    literalsByStem.set(stem, (literalsByStem.get(stem) ?? new Set()).add(leader));
  }

  const collapsing = [...literalsByStem].filter(([, set]) =>
    [...set].some((l) => l !== bare(l)),
  );
  const hasRival = collapsing.filter(([, set]) => set.size > 1);
  const substitutes = hasRival.filter(([stem, set]) => [...set].some((l) => l.toLowerCase() === stem));

  it("pins every stem a printing number can collapse", () => {
    const got = Object.fromEntries(
      collapsing.map(([stem, set]) => [stem, [...set].sort()]).sort(),
    );
    expect(got).toEqual({
      aurora: ["Aurora 2"],
      caine: ["Caine", "Caine 4"],
      lylyth: ["Lylyth", "Lylyth 1", "Lylyth 3"],
      skarre: ["Skarre 1", "Skarre 3"],
    });
    expect(hasRival.map(([s]) => s).sort()).toEqual(["caine", "lylyth", "skarre"]);
    expect(substitutes.map(([s]) => s).sort()).toEqual(["caine", "lylyth"]);
  });

  it("keeps a stem with no bare row inside a single army", () => {
    /*
      An exclusion written as an assertion rather than a comment, because it is
      a COINCIDENCE and not a guarantee. "Aurora 2" and the two Skarres each sit
      in one army, which is why neither needs the badge to pick between armies.
      Nothing enforces that: a "Skarre 4" printed into a second Cryx army would
      break it silently, and the answer would become an arbitrary army with no
      bare row to fall back on. Assert it so it fails when it stops being true.

      Scoped to stems with no bare row on purpose. Caine and Lylyth already span
      several armies, which is the ambiguity the sets above pin.
    */
    for (const [stem, set] of collapsing) {
      if ([...set].some((l) => l.toLowerCase() === stem)) continue;
      const armies = new Set(
        rows.filter((r) => bare(r.leader).toLowerCase() === stem).map((r) => r.info.army),
      );
      expect([...armies], `${stem} now spans more than one army`).toHaveLength(1);
    }
  });
});
