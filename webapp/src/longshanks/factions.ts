/**
 * The armies of Warmachine, the factions they belong to, and who leads them.
 *
 * Two jobs, both of which exist because Longshanks tells us less than the owner
 * needs at pairing time.
 *
 * The first is the badge. Longshanks shows a faction as a small logo, and those
 * logos are Privateer Press artwork -- not ours to ship. A two-letter code on the
 * faction's colour reads the same way at arm's length across a table and belongs
 * to nobody, so that is what the app draws instead. The codes are hand-assigned
 * rather than derived: initials collide (Dark Host and Dragon's Host, Sea Raiders
 * and Shadows of the Retribution), and a badge that means two things is worse
 * than no badge at all.
 *
 * The second is the leader. Before an event has been played there are no game
 * rows to read a leader off, only the army lists players have registered, and a
 * list is free text -- a title someone made up, then a few hundred model names.
 * Nothing in it is marked "this is the caster". What makes it recoverable is that
 * the set of possible leaders is small and closed: an army has at most seven, so
 * finding which of those seven appears in the text is a lookup rather than a
 * guess. See {@link findLeader}.
 *
 * The names here are Longshanks' own -- taken from the same taxonomy its event
 * pages use, by way of the sibling QTR_CorvidGrudge catalogue -- including the
 * spellings it gets wrong (`Huxely`). That is deliberate. The point of this table
 * is to agree with Longshanks, so a leader parsed out of an army list and a leader
 * parsed out of a game row are the same string and dedupe against each other.
 * Correcting a spelling here would quietly create two leaders where there is one.
 */

export interface ArmyInfo {
  /** The army / subfaction as Longshanks names it, e.g. "Storm Legion". */
  army: string;
  /** The parent faction, e.g. "Cygnar". */
  faction: string;
  /** Two-letter badge code, unique across every army in this table. */
  code: string;
  /** The faction's colour, used as the badge background. */
  color: string;
  /** Every leader Longshanks lists for this army. */
  leaders: string[];
}

export const ARMIES: ArmyInfo[] = [
  { army: "5th Division", faction: "Khador", code: "5D", color: "#dc2626", leaders: ["Butcher", "Malakov", "Sorscha", "Strakhov"] },
  { army: "Armored Korps", faction: "Khador", code: "AK", color: "#dc2626", leaders: ["Harkevich", "Irusk", "Karchev", "Sorscha"] },
  { army: "Army of the Western Reaches", faction: "Skorne", code: "WR", color: "#c2410c", leaders: ["Jalaam", "Makeda", "Xerxis", "Zaadesh"] },
  { army: "Blackfleet", faction: "Cryx", code: "BF", color: "#15803d", leaders: ["Aiakos", "Rahera", "Skarre 1", "Skarre 3"] },
  { army: "Blindwater Congregation", faction: "Mercenaries", code: "BW", color: "#4b5563", leaders: ["Barnabas", "Calaban", "Jaga-Jaga", "Maelok"] },
  { army: "Brineblood Marauders", faction: "Southern Kriels", code: "BM", color: "#0891b2", leaders: ["Bagadibawm", "Firequill", "Foulblood", "Ragemonger", "Shadowtongue", "Thorga"] },
  { army: "Convergence of Cyriss", faction: "Convergence of Cyriss", code: "CC", color: "#0369a1", leaders: ["Aurora 2", "Axis", "Directrix", "Lucant", "Orion", "Syntherion"] },
  { army: "Crucible Guard", faction: "Crucible Guard", code: "CG", color: "#ca8a04", leaders: ["Bennet", "Gearhart", "Locke", "Lukas", "Mackay", "Syvestro"] },
  { army: "Dark Host", faction: "Cryx", code: "DH", color: "#15803d", leaders: ["Agathia", "Deneghra", "Goreshade", "Scaverous"] },
  { army: "Dark Operations", faction: "Mercenaries", code: "DO", color: "#4b5563", leaders: ["Cyphon", "Khythos", "Thexus"] },
  { army: "Devourer's Host", faction: "Circle Orboros", code: "DV", color: "#047857", leaders: ["Iona", "Kromac", "Tanith", "Wurmwood"] },
  { army: "Dragon's Host", faction: "Legion of Everblight", code: "DR", color: "#4338ca", leaders: ["Absylonia", "Anamag", "Kallus", "Thagrosh"] },
  { army: "Exalted", faction: "Skorne", code: "EX", color: "#c2410c", leaders: ["Hexeris", "Mordikaar", "Xekaar", "Zaal"] },
  { army: "Fane of Nyrro", faction: "Dusk", code: "FN", color: "#7c3aed", leaders: ["Ashmael", "Hysene", "Nymara", "Vorsalys"] },
  { army: "Final Interdiction", faction: "Protectorate of Menoth", code: "FI", color: "#b45309", leaders: ["Cyrenia", "Kreoss", "Reznik", "Severius"] },
  { army: "First Army", faction: "Cygnar", code: "FA", color: "#2563eb", leaders: ["Brisbane", "Caine", "Darius", "Kraye"] },
  { army: "Gravediggers", faction: "Cygnar", code: "GD", color: "#2563eb", leaders: ["Caine", "Cyn", "Hasker", "Jakes", "McCoy", "Sparkhammer", "Vargus"] },
  { army: "Grymkin", faction: "Grymkin", code: "GK", color: "#e11d48", leaders: ["Old Witch", "The Child", "The Dreamer", "The Heretic", "The King of Nothing", "The Wanderer"] },
  { army: "House Kallyss", faction: "Dusk", code: "HK", color: "#7c3aed", leaders: ["Hazaroth", "Hellyth", "Morayne", "Scyrafael", "Tyrus"] },
  { army: "Infernals", faction: "Infernals", code: "IN", color: "#9333ea", leaders: ["Agathon", "Omodamos", "Vorgoroth", "Zaateroth"] },
  { army: "Kithguard", faction: "Southern Kriels", code: "KG", color: "#0891b2", leaders: ["Bagadibawm", "Craghorn", "Grimtusk", "Gunnbjorn", "Stormcraw", "Wroughtmourn"] },
  { army: "Legions of Dawn", faction: "Retribution of Scyrah", code: "LD", color: "#0f766e", leaders: ["Helynna", "Issyria", "Ossyan", "Vyros"] },
  { army: "Necrofactorium", faction: "Cryx", code: "NF", color: "#15803d", leaders: ["Dekathus", "Eviscerus", "Khythos", "Mortenebra", "Nekane", "Sepsira"] },
  { army: "Old Umbrey", faction: "Khador", code: "OU", color: "#dc2626", leaders: ["Azlanov", "Kovoskiy", "Lesnoi", "Lissya", "Morozov", "Reznikova"] },
  { army: "Ravens of War", faction: "Legion of Everblight", code: "RW", color: "#4338ca", leaders: ["Kryssa", "Lylyth 1", "Lylyth 3", "Vayl"] },
  { army: "Rhul Guard", faction: "Mercenaries", code: "RG", color: "#4b5563", leaders: ["Durgen", "Gorten", "Ossrum"] },
  { army: "Sea Raiders", faction: "Orgoth", code: "SR", color: "#7f1d1d", leaders: ["Butcher", "Horruskh", "Kishtaar", "Oriax", "Sabbreth"] },
  { army: "Secret Dominion", faction: "Circle Orboros", code: "SD", color: "#047857", leaders: ["Baldur", "Grayle", "Krueger", "Thorle"] },
  { army: "Shadowflame Shard", faction: "Khymaera", code: "SS", color: "#0284c7", leaders: ["Kyrrax", "Lylyth", "Nyxyan", "Rassyk", "Shyryss", "Vallyx"] },
  { army: "Shadows of the Retribution", faction: "Retribution of Scyrah", code: "SH", color: "#0f766e", leaders: ["Garryth", "Kaelyssa", "Ravyn", "Thyron"] },
  { army: "Soldiers of Fortune", faction: "Mercenaries", code: "SF", color: "#4b5563", leaders: ["Ashlynn", "Damiano", "MacBain", "Magnus"] },
  { army: "Storm Knights", faction: "Cygnar", code: "SK", color: "#2563eb", leaders: ["Jakes", "Maddox", "Nemo", "Stryker"] },
  { army: "Storm Legion", faction: "Cygnar", code: "SL", color: "#2563eb", leaders: ["Caine 4", "Calder", "Di Baro", "Huxely", "Sparkhammer", "Wolfe"] },
  { army: "Storm of the North", faction: "Trollbloods", code: "SN", color: "#4d7c0f", leaders: ["Borka", "Doomshaper", "Grim", "Kolgrima"] },
  { army: "Talion Charter", faction: "Mercenaries", code: "TC", color: "#4b5563", leaders: ["Fiona", "Montador", "Rahera", "Shae"] },
  { army: "Temple Guardians", faction: "Protectorate of Menoth", code: "TG", color: "#b45309", leaders: ["Amon", "Feora", "Malekus", "Thyra"] },
  { army: "Thornfall Alliance", faction: "Mercenaries", code: "TA", color: "#4b5563", leaders: ["Arkadius", "Carver", "Helga", "Midas", "Sturm & Drang"] },
  { army: "United Kriels", faction: "Trollbloods", code: "UK", color: "#4d7c0f", leaders: ["Grissel", "Gunnbjorn", "Jarl", "Madrak"] },
  // Longshanks' catch-all for legacy armies. Its "leaders" are faction names
  // rather than models, so it carries none -- there is nothing here to match a
  // list against, and pretending otherwise would produce nonsense leaders.
  { army: "Unlimited", faction: "Unlimited", code: "UL", color: "#6b7280", leaders: [] },
  { army: "Winter Korps", faction: "Khador", code: "WK", color: "#dc2626", leaders: ["Baranova", "Borisyuk", "Kovoskiy", "Savaryn", "Sikora", "Vilkul"] },
];

const BY_ARMY = new Map(ARMIES.map((a) => [a.army.toLowerCase(), a]));

/** The table entry for an army, by its Longshanks name. Case-insensitive. */
export function armyInfo(army: string | undefined | null): ArmyInfo | undefined {
  if (!army) return undefined;
  return BY_ARMY.get(army.trim().toLowerCase());
}

/**
 * The armies a Longshanks badge could be pointing at.
 *
 * The badge Longshanks shows against a player is titled with an army for some
 * players and with the parent faction for others -- "Clockwork Legions" and
 * "Convergence of Cyriss" both turn up in the same event. Read as an army name
 * a faction matches nothing, which silently throws away the only hint there is,
 * so a faction is resolved to every army beneath it instead. That is a weaker
 * hint than one army, but a weak hint beats none.
 */
function hintedArmies(hint: string | undefined | null): ArmyInfo[] {
  const exact = armyInfo(hint);
  if (exact) return [exact];
  const name = hint?.trim().toLowerCase();
  return name ? ARMIES.filter((a) => a.faction.toLowerCase() === name) : [];
}

/**
 * Spellings a list uses that Longshanks' own leader name does not.
 *
 * Longshanks names a leader by whichever of their names is shortest and most
 * recognisable, and a list writes whatever is printed on the card, so the two
 * diverge whenever a character is better known by a title than by a name:
 * "Old Witch" is written "Zevanna Agha, the Fate Keeper", and the Sea Raiders'
 * "Butcher" is written "Orsus the Betrayed".
 *
 * `Huxely` is a different case -- it is Longshanks' typo, not an alias. Fixing
 * the table entry is not an option, because these names have to keep matching
 * the ones parsed out of game rows, so the wrong spelling stays and the right
 * one is searched for beside it.
 */
const ALIASES: Record<string, string[]> = {
  Butcher: ["Orsus"],
  Huxely: ["Huxley"],
  "Old Witch": ["Zevanna"],
};

/**
 * A leader name without its Longshanks disambiguating number.
 *
 * The number distinguishes reprints of one character ("Caine 4" is the Storm
 * Legion Caine) and is Longshanks bookkeeping, so it never appears in a list.
 */
function bare(leader: string): string {
  return leader.replace(/\s+\d+$/, "");
}

/**
 * The spellings to look for when hunting this leader in an army list.
 *
 * Longshanks stores a leader by a short name -- "Stormcraw", "Caine 4" -- while
 * the list writes the model out in full: "Major Abraham Stormcraw". The short
 * name is a substring of the long one, which is what makes the match work at
 * all.
 */
function needles(leader: string): string[] {
  const base = bare(leader);
  return [base, ...(ALIASES[leader] ?? ALIASES[base] ?? [])];
}

/**
 * Does the list name this model?
 *
 * Anchored at the start of a word but deliberately open at the end. A leader's
 * Longshanks name is a prefix of what the list calls them, not the whole of it
 * -- "Cyn" is written "Captain Cynthia Rosko" -- so requiring a boundary on the
 * right would miss the common case. Requiring one on the left still stops a
 * name matching inside an unrelated word.
 *
 * The looseness that buys is paid for in {@link findLeader}, which drops a hit
 * whose name is a prefix of another hit: "Grim" and "Grimtusk" are both leaders,
 * and a list naming the second matches the first here too.
 */
function mentions(text: string, name: string): boolean {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?:^|[^a-z])${escaped}`, "i").test(text);
}

/**
 * The lines of a list that cost nothing.
 *
 * A list body prices every entry it charges for -- "14 Sybaris", "9 Vordak" --
 * and leaves the warcaster unpriced, because the caster comes with the army
 * rather than out of the points. Characters bought as models are priced, which
 * is what separates "Auricant Vorsalys" leading the list from "Ashmael" being in
 * it. Not decisive on its own (free entries also include attachments like
 * "Drone Servitor", which are not leaders and not in this table), but exactly
 * the distinction needed once two of an army's leaders are both named.
 */
function unpriced(listText: string): string {
  return listText
    .split("\n")
    .filter((line) => !/^\s*\d/.test(line))
    .join("\n");
}

/**
 * Where in the list a model is first named, or -1.
 *
 * A Grand Melee list can field two warcasters, and the one written first is the
 * one the player leads with -- and the one their list title almost always refers
 * to. That ordering is the only thing distinguishing them, so it has to survive
 * into the answer.
 */
function firstMention(text: string, name: string): number {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|[^a-z])${escaped}`, "i").exec(text);
  return m ? m.index : -1;
}

/**
 * Which leader an army list is led by, if it can be told with confidence.
 *
 * Searches the whole list text rather than trying to find the caster's line,
 * because there is no reliable line to find: a list may open with the army, or
 * with a title someone typed, and the free entries at the top include attached
 * models as often as not. What the text always contains, somewhere, is the
 * leader's name.
 *
 * `armyHint` -- the badge Longshanks shows against that player -- is applied
 * first, which is what makes the answer trustworthy: within one army the leaders
 * are distinct people. Where more than one is named, {@link unpriced} separates
 * the casters the army comes with from characters the list bought, and position
 * separates a two-caster Grand Melee list's leader from its second. Only if the
 * hint yields nothing does the search widen to every army, since players do
 * bring a list from a second army and Longshanks shows just one badge.
 *
 * Returns undefined rather than a best guess. A wrong leader on the board is
 * worse than a blank one: blank prompts a look at the real list, wrong does not.
 */
export function findLeader(
  listText: string,
  armyHint?: string,
): { leader: string; army: string } | undefined {
  const hinted = hintedArmies(armyHint);
  const inHint = new Set(hinted.map((a) => a.army));
  const free = unpriced(listText);

  let hits: { leader: string; army: string; free: boolean; at: number }[] = [];
  for (const info of ARMIES) {
    for (const leader of info.leaders) {
      const spellings = needles(leader);
      const found = spellings.map((n) => firstMention(free, n)).filter((i) => i >= 0);
      if (found.length) {
        hits.push({ leader, army: info.army, free: true, at: Math.min(...found) });
      } else if (spellings.some((n) => mentions(listText, n))) {
        hits.push({ leader, army: info.army, free: false, at: -1 });
      }
    }
  }

  // Every army is searched before the hint is applied, because a shorter name
  // that is a prefix of a longer one matched the same words and the longer name
  // is the model the list actually contains -- and the two are rarely in the
  // same army. "Grim" leads Storm of the North, "Grimtusk" leads Kithguard, and
  // pruning within the hinted army alone would answer "Grim" every time.
  const names = hits.map((h) => bare(h.leader));
  hits = hits.filter(
    (_, i) => !names.some((n, j) => j !== i && n !== names[i] && n.startsWith(names[i])),
  );

  type Hit = (typeof hits)[number];

  /** The leader among these hits, or nothing when they cannot be told apart. */
  const settle = (pool: Hit[]): { leader: string; army: string } | undefined => {
    const distinct = (p: Hit[]) => new Set(p.map((h) => bare(h.leader))).size;
    // The same person can lead two armies ("Caine" is in both First Army and
    // Gravediggers): still one answer, only the attribution is uncertain.
    if (distinct(pool) === 1) return { leader: pool[0].leader, army: pool[0].army };

    // Two or more real candidates. Only the ones the list did not pay points for
    // can be leading it; among those, the first one written leads.
    const casters = pool.filter((h) => h.free).sort((a, b) => a.at - b.at);
    return casters.length ? { leader: casters[0].leader, army: casters[0].army } : undefined;
  };

  if (inHint.size) {
    const own = hits.filter((h) => inHint.has(h.army));
    if (own.length) return settle(own);
  }

  // Nothing from the hinted army: the player brought a list from a second one.
  const wide = hits.filter((h) => !inHint.has(h.army));
  return wide.length ? settle(wide) : undefined;
}
