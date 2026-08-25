/**
 * Rating scales.
 *
 * Two things have to be true at once here.
 *
 * Teams are attached to the scale they already use. Australia brought a
 * three-colour sheet to WTC 2024; England have used 1-10 for years; this app's
 * desktop build has always defaulted to 1-5. Telling any of them they are
 * holding it wrong is a good way to be uninstalled.
 *
 * But resolution is not cosmetic. Finding 14 measured it: on the same 25
 * matchups, a 5-level scale separated 6 distinct boards where a 7-level scale
 * separated 13. Coarser scales genuinely throw away decisions.
 *
 * Both are satisfied by making the scale a display concern. Every rating is
 * stored as a fraction of the way from the worst matchup to the best, so the
 * engine only ever sees a normalised board and the even threshold stays exactly
 * midway regardless. Changing scale re-labels the buttons; it never rewrites
 * what was meant, and a board entered on one scale can be read on another.
 */

export interface Scale {
  id: string;
  label: string;
  min: number;
  max: number;
  /** Step between selectable values. */
  step: number;
  hint: string;
}

export const SCALES: Scale[] = [
  {
    id: "stoplight",
    label: "Stoplight",
    min: 1,
    max: 3,
    step: 1,
    hint: "Red dodge, yellow even, green wanted. What Australia used in 2024.",
  },
  {
    id: "five",
    label: "1-5",
    min: 1,
    max: 5,
    step: 1,
    hint: "The desktop app's default.",
  },
  {
    id: "fiveHalf",
    label: "1-5, half steps",
    min: 1,
    max: 5,
    step: 0.5,
    hint: "Same habits, twice the resolution.",
  },
  {
    id: "ten",
    label: "1-10",
    min: 1,
    max: 10,
    step: 1,
    hint: "The English convention.",
  },
  {
    id: "twenty",
    label: "1-20",
    min: 1,
    max: 20,
    step: 1,
    hint: "Fine enough to separate boards a 1-5 sheet collapses.",
  },
  {
    id: "hundred",
    label: "0-100",
    min: 0,
    max: 100,
    step: 5,
    hint: "Win percentage, if you think in those terms.",
  },
];

export const scaleById = (id: string): Scale => SCALES.find((s) => s.id === id) ?? SCALES[1];

/** Every selectable value on a scale, worst first. */
export function scaleValues(scale: Scale): number[] {
  const out: number[] = [];
  for (let v = scale.min; v <= scale.max + 1e-9; v += scale.step) {
    out.push(Number(v.toFixed(2)));
  }
  return out;
}

/** Midpoint of a scale: the matchup that is neither wanted nor dodged. */
export const scaleMidpoint = (scale: Scale): number => (scale.min + scale.max) / 2;

/**
 * Where a rating sits between the worst and best matchup, as 0..1.
 *
 * This is what gets stored, so a board survives a change of scale.
 */
export const toFraction = (value: number, scale: Scale): number =>
  scale.max === scale.min ? 0.5 : (value - scale.min) / (scale.max - scale.min);

/** Read a stored fraction back out on a scale, snapped to a selectable value. */
export function fromFraction(fraction: number, scale: Scale): number {
  const raw = scale.min + fraction * (scale.max - scale.min);
  const steps = Math.round((raw - scale.min) / scale.step);
  const snapped = scale.min + steps * scale.step;
  return Number(Math.min(scale.max, Math.max(scale.min, snapped)).toFixed(2));
}

/**
 * Colour for a rating, on the red-yellow-green axis every team already reads.
 *
 * Driven by the fraction, so the same matchup looks the same on every scale.
 */
export function ratingColor(fraction: number): string {
  const f = Math.min(1, Math.max(0, fraction));
  // Interpolate through amber rather than straight red-to-green, so the middle
  // reads as "even" instead of as a muddy blend.
  const stops: [number, [number, number, number]][] = [
    [0, [198, 40, 40]],
    [0.5, [214, 158, 46]],
    [1, [46, 138, 74]],
  ];
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (f >= stops[i][0] && f <= stops[i + 1][0]) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const span = hi[0] - lo[0] || 1;
  const t = (f - lo[0]) / span;
  const c = lo[1].map((v, i) => Math.round(v + (hi[1][i] - v) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}
