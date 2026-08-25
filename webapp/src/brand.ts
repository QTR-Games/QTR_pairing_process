/*
  Every brand string and outbound link in one file.

  The logo and the wordmark are explicitly placeholders. Keeping them here means
  replacing them is a one-file edit rather than a search across components, and
  it keeps the raven out of the component tree so a future logo of a different
  aspect ratio does not require touching layout code.
*/
import ravenUrl from "./assets/gronksoft-raven.png";

export const BRAND = {
  /** 264x256 placeholder. Rendered at 128px so it never upscales. */
  logo: ravenUrl,
  name: "GronkSoft",
  product: "QTR Pairing",
  tagline: "Pairing maths for team tournaments",
} as const;

/**
 * Outbound links.
 *
 * `bugs` points at the real issue tracker and works today. `beer` is a
 * placeholder: until it is a real address the menu hides that item rather than
 * showing a button that goes nowhere, because a dead control at a table is
 * worse than a missing one.
 */
export const LINKS = {
  bugs: "https://github.com/QTR-Games/QTR_pairing_process/issues/new",
  beer: "",
} as const;
