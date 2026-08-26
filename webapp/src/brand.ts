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
  /** The studio. Shown on the splash, which is a publisher card. */
  name: "GronkSoft",
  /**
   * The product.
   *
   * Named for the sound dice make in a closed hand -- the moment just before a
   * round is decided, which is the moment this app is for. The repository is
   * still `QTR_pairing_process` and the Python tooling still carries the old
   * name; only the shipped app is KLIK KLAK.
   */
  product: "KLIK KLAK",
  tagline: "Pairing maths for team tournaments",
} as const;

/**
 * Outbound links.
 *
 * Both point at real addresses today. `beer` is the same Ko-fi page the sibling
 * app (QTR_CorvidGrudge) links to, so the two share one destination rather than
 * splitting supporters across two.
 *
 * The menu still guards on the value being non-empty. That guard is not dead
 * code: it is what lets either link be blanked here, in one place, without
 * shipping a control that goes nowhere -- and a dead button at a table is worse
 * than a missing one.
 */
export const LINKS = {
  bugs: "https://github.com/QTR-Games/QTR_pairing_process/issues/new",
  beer: "https://ko-fi.com/quotemyname",
} as const;
