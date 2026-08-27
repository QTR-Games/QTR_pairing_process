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
export const pct = (p: number): string =>
  p > 0 && p < 0.005 ? "under 1%" : `${Math.round(p * 100)}%`;
