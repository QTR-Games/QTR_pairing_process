/**
 * App-wide settings, as opposed to per-board data.
 *
 * These are preferences about how the app behaves, not facts about a round, so
 * they live in their own key rather than riding along inside a `Board`. A
 * setting changed while looking at one board should still hold when the next
 * one is opened.
 *
 * Same storage rules as `board.ts`: localStorage only, no network, and every
 * read tolerates finding nothing or finding rubbish. An event-day app that
 * throws on a corrupt preference is worse than one that quietly uses defaults.
 */

/**
 * How much the screen should say about the worst matchup on the board.
 *
 * Three states rather than a checkbox, because "on" and "off" turned out not to
 * cover it. Measured over all 31 saved boards, the dodge insight has something
 * to say on 31 of them -- there is no board where it stays quiet on its own. So
 * a plain on/off switch is really a choice between "one more permanent line on
 * every screen" and "a feature you own but never see".
 *
 *  - `off`      -- never shown, and never computed
 *  - `onDemand` -- a button offers it; nothing is computed until you tap
 *  - `always`   -- shown inline with the other readings
 *
 * `off` and `onDemand` both skip the solve, which is the point: pricing a dodge
 * costs around 20ms on a laptop and several times that on a phone, and it runs
 * again on every rating change. Hiding the output while still paying for it
 * would be the worst of both.
 */
export type DodgeMode = "off" | "onDemand" | "always";

export const DODGE_MODES: { id: DodgeMode; label: string }[] = [
  { id: "onDemand", label: "When I ask" },
  { id: "always", label: "Always" },
  { id: "off", label: "Never" },
];

/**
 * How much the live round explains itself.
 *
 * The engine prices every decision the same way regardless of this setting --
 * the toggle changes what the screen says, never what it computes. It exists
 * because the two captains this app is for want opposite things from the same
 * position. A newer captain distrusts a silent recommendation with a weekend on
 * the line and wants the reasoning behind every pick; a WTC veteran already
 * knows the theory and wants the grid, the numbers and nothing in the way.
 *
 *  - `full`  -- every "why": the tie-break reasoning, the hold-or-play read,
 *               the upside-if-they-err line, and a note on forced pairings
 *  - `brief` -- the recommendation only ("take X"), the value and the raw
 *               rating chip; none of the explanatory prose
 *  - `off`   -- just the tappable options and their numbers, no advice at all
 *
 * Unlike the dodge price, none of these skip a solve: the round is already
 * searched for the options themselves, so the prose is free to render or hide.
 */
export type AdviceLevel = "full" | "brief" | "off";

export const ADVICE_LEVELS: { id: AdviceLevel; label: string }[] = [
  { id: "full", label: "Full explanations" },
  { id: "brief", label: "Just the picks" },
  { id: "off", label: "No advice" },
];

/** Experimental: flag unusual opponent moves during a live round. */
export type SurpriseMode = "off" | "on";

export const SURPRISE_MODES: { id: SurpriseMode; label: string }[] = [
  { id: "off", label: "Off" },
  { id: "on", label: "On (experimental)" },
];

/**
 * The currency a Verdict insight card speaks: rating points, or round-win %.
 *
 * The engine computes both for every card, so this is purely a display choice.
 * It is per-card, not app-wide, because the cards do not all read the same way
 * in each currency. The dice-off gap is a board-independent constant in points
 * (a clean "going first is worth N") but a flat ~8pp in chance that carries no
 * board-specific information, so its natural default is points; the protection
 * and trade-off cards are decisions about taking the round, so they default to
 * chance. Every card stays individually switchable regardless of its default.
 */
export type CardUnit = "points" | "chance";

/** The Verdict insight cards that can switch currency. */
export type CardId = "protocolProtects" | "beingHunted" | "diceOff" | "tradeOff" | "hiddenTie";

export const CARD_IDS: readonly CardId[] = [
  "protocolProtects",
  "beingHunted",
  "diceOff",
  "tradeOff",
  "hiddenTie",
];

/**
 * The currency each card shows until the user says otherwise.
 *
 * Owner-set: everything that is a decision about taking the round reads in
 * chance; the dice-off, whose chance form is a constant, keeps points.
 */
export const CARD_UNIT_DEFAULTS: Record<CardId, CardUnit> = {
  protocolProtects: "chance",
  beingHunted: "chance",
  diceOff: "points",
  tradeOff: "chance",
  hiddenTie: "chance",
};

export interface Settings {
  dodgeMode: DodgeMode;
  adviceLevel: AdviceLevel;
  surpriseMode: SurpriseMode;
  /** Minimum points of opponent regret before we raise a surprise flag. */
  surpriseRegretThreshold: number;
  /**
   * Per-card currency overrides. Only cards the user has explicitly switched
   * appear here; everything else falls back to `CARD_UNIT_DEFAULTS`, so the
   * defaults can evolve without rewriting saved preferences.
   */
  cardUnits: Partial<Record<CardId, CardUnit>>;
}

/**
 * Ask-first is the default deliberately.
 *
 * The insight is genuinely useful -- the worst matchup is worth a mean 8.2% of
 * the round and up to 15.9% -- but it is not useful on every board at every
 * moment, and screen space at a table is the scarcest thing there is.
 */
export const DEFAULTS: Settings = {
  dodgeMode: "onDemand",
  adviceLevel: "full",
  surpriseMode: "off",
  surpriseRegretThreshold: 0,
  cardUnits: {},
};

const KEY = "qtr.settings.v1";

const isDodgeMode = (v: unknown): v is DodgeMode =>
  v === "off" || v === "onDemand" || v === "always";

const isAdviceLevel = (v: unknown): v is AdviceLevel =>
  v === "full" || v === "brief" || v === "off";

const isSurpriseMode = (v: unknown): v is SurpriseMode => v === "off" || v === "on";

const isCardUnit = (v: unknown): v is CardUnit => v === "points" || v === "chance";

const asNonNegativeNumber = (v: unknown): number | null => {
  if (typeof v !== "number" || !Number.isFinite(v) || v < 0) return null;
  return v;
};

/**
 * Keep only known cards mapped to a valid currency.
 *
 * Same tolerance as every other field: an unknown card id or a junk value is
 * dropped rather than trusted, so a preferences file from a future version (a
 * card that no longer exists, a third currency) degrades to defaults instead of
 * putting an unrenderable unit in front of a captain.
 */
const sanitizeCardUnits = (v: unknown): Partial<Record<CardId, CardUnit>> => {
  const out: Partial<Record<CardId, CardUnit>> = {};
  if (!v || typeof v !== "object") return out;
  const source = v as Record<string, unknown>;
  for (const id of CARD_IDS) {
    if (isCardUnit(source[id])) out[id] = source[id] as CardUnit;
  }
  return out;
};

/** The currency a card should show, resolving the user's choice against defaults. */
export const resolveCardUnit = (
  cardUnits: Partial<Record<CardId, CardUnit>>,
  id: CardId,
): CardUnit => cardUnits[id] ?? CARD_UNIT_DEFAULTS[id];

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<Settings>;
    // Field by field rather than trusting the shape. A settings file written by
    // a future version should degrade to defaults, not crash the app.
    return {
      dodgeMode: isDodgeMode(parsed?.dodgeMode) ? parsed.dodgeMode : DEFAULTS.dodgeMode,
      adviceLevel: isAdviceLevel(parsed?.adviceLevel)
        ? parsed.adviceLevel
        : DEFAULTS.adviceLevel,
      surpriseMode: isSurpriseMode(parsed?.surpriseMode)
        ? parsed.surpriseMode
        : DEFAULTS.surpriseMode,
      surpriseRegretThreshold:
        asNonNegativeNumber(parsed?.surpriseRegretThreshold) ?? DEFAULTS.surpriseRegretThreshold,
      cardUnits: sanitizeCardUnits(parsed?.cardUnits),
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings: Settings): Settings {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // Out of quota, or storage disabled. The in-memory setting still applies
    // for this session, which is the part that matters during a round.
  }
  return settings;
}

/**
 * Flip one card's currency and persist, leaving every other preference alone.
 *
 * A read-modify-write against the live stored settings rather than against a
 * value held in a component, because the cards are the only writer of
 * `cardUnits` and App.tsx round-trips the rest of the object independently.
 * Merging here means a card toggle can never clobber a dodge-mode change made in
 * the same session, and vice versa.
 */
export function setCardUnit(id: CardId, unit: CardUnit): Settings {
  const current = loadSettings();
  return saveSettings({ ...current, cardUnits: { ...current.cardUnits, [id]: unit } });
}
