/**
 * Display formatting shared across every screen, so the app speaks one dialect.
 *
 * Percentages are shown as whole rounds per hundred, never as raw decimals. A
 * tenth of a percentage point here is fabricated precision: `SPREAD` in
 * winProbability.ts is an anchoring choice that has never been fitted against
 * results, so "62.4%" claims a resolution the model does not have while "62%"
 * says the same true thing. Every consumer is meant to read these as an
 * ORDERING over options, not a forecast for the round.
 *
 * Rounding a real but sub-half-point figure down to a bare "0%" would be a
 * different lie -- a cost that is not zero is not free -- so it is named
 * ("under 1%") rather than printed as nothing. That band is deliberately the
 * counterpart to the engine's `free` flag (`price < 1e-9` in avoidance.ts): a
 * dodge the engine calls not-free can never display as "0%", so the app cannot
 * say "costs 0%" from the formatter and "not free" from the engine at once.
 *
 * This is the single source of truth for the convention. Both levels (a win
 * chance) and small differences (the price of a dodge) route through here.
 */

import type { Unit } from "./settings";
export const pct = (p: number): string =>
  p > 0 && p < 0.005 ? "under 1%" : `${Math.round(p * 100)}%`;

/**
 * The other dialect: a rating or a round total, in points.
 *
 * Ratings are whole numbers on every shipped scale, and a total of five of them
 * is whole too, so the common case prints bare. Sampled figures (the typical
 * outcome across a reply space) are not, and a tenth is the most those deserve.
 */
export const points = (n: number): string =>
  Number.isInteger(n) ? String(n) : n.toFixed(1);

/**
 * A quantity already computed in the currency asked for, rendered in it.
 *
 * The value arrives pre-priced rather than as a number plus a conversion,
 * because the two currencies are not a conversion of each other. A round total
 * is a sum of five ratings; its chance counterpart is the probability of taking
 * the round from the position that total describes. Only the engine can produce
 * the second, so producing it stays the caller's job and this stays formatting.
 */
export const inUnit = (unit: Unit, value: number): string =>
  unit === "chance" ? pct(value) : points(value);

/**
 * The size of a difference, without a sign, in the currency it was priced in.
 *
 * Differences get their own entry point because `pct`'s "under 1%" band is
 * about a level, and a caller subtracting two levels can land on a negative.
 * Taking the magnitude here keeps that band meaningful and leaves the sign to
 * the call site, which is the only place that knows whether it reads as "+3%"
 * in a list or "worth 3% more" in a sentence.
 */
export const gapInUnit = (unit: Unit, value: number): string =>
  inUnit(unit, Math.abs(value));
