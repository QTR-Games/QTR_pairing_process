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
  tagline: "Play like you've got a pairing.",
} as const;

export function getBugReportUrl(): string {
  const defaultUrl = "https://github.com/QTR-Games/QTR_pairing_process/issues/new";
  if (typeof window === "undefined") {
    return defaultUrl;
  }

  const ua = typeof navigator !== "undefined" ? navigator.userAgent || "" : "";
  const platform = typeof navigator !== "undefined" ? navigator.platform || "" : "";
  const language = typeof navigator !== "undefined" ? navigator.language || "" : "";
  const onLine = typeof navigator !== "undefined" ? navigator.onLine : true;

  // Determine OS
  let os = "Unknown";
  if (/android/i.test(ua)) {
    os = "Android";
  } else if (/ipad|iphone|ipod/i.test(ua)) {
    os = "iOS";
  } else if (/macintosh|mac os x/i.test(ua)) {
    os = "macOS";
  } else if (/windows|win32/i.test(ua)) {
    os = "Windows";
  } else if (/linux/i.test(ua)) {
    os = "Linux";
  } else if (platform) {
    os = platform;
  }

  // Determine Browser
  let browser = "Other / WebView";
  if (/chrome|crios/i.test(ua) && !/edge|edg/i.test(ua) && !/opr/i.test(ua)) {
    browser = "Chrome";
  } else if (/safari/i.test(ua) && !/chrome|crios/i.test(ua)) {
    browser = "Safari";
  } else if (/firefox|fxios/i.test(ua)) {
    browser = "Firefox";
  } else if (/edge|edg/i.test(ua)) {
    browser = "Edge";
  } else if (/opr/i.test(ua)) {
    browser = "Opera";
  }

  // Determine App Environment
  let appEnv = "Web Browser";
  const isTauri = "__TAURI_INTERNALS__" in window || "__TAURI__" in window;
  const isCapacitor = "Capacitor" in window;
  const isStandalone = 
    typeof window.matchMedia === "function" && window.matchMedia("(display-mode: standalone)").matches || 
    (typeof navigator !== "undefined" && (navigator as any).standalone === true);

  if (isTauri) {
    appEnv = "Tauri Desktop";
  } else if (isCapacitor) {
    appEnv = "Capacitor Mobile";
  } else if (isStandalone) {
    appEnv = "Standalone PWA";
  }

  const screenWidth = window.screen?.width || 0;
  const screenHeight = window.screen?.height || 0;
  const dpr = window.devicePixelRatio || 1;
  const viewportWidth = window.innerWidth || 0;
  const viewportHeight = window.innerHeight || 0;

  const diagnostics = [
    "--- Client Diagnostics ---",
    `App Environment: ${appEnv}`,
    `User Agent: ${ua}`,
    `OS: ${os}`,
    `Browser: ${browser}`,
    `Screen Resolution: ${screenWidth}x${screenHeight} (DPR: ${dpr})`,
    `Viewport: ${viewportWidth}x${viewportHeight}`,
    `Connection Status: ${onLine ? "Online" : "Offline"}`,
    `Language: ${language}`
  ].join("\n");

  try {
    const params = new URLSearchParams();
    params.append("template", "bug_report.yml");
    params.append("area", "Web app (phone / browser)");
    params.append("version", "2.1.4");
    params.append("python", `${os} / ${browser}`);
    params.append("logs", diagnostics);
    return `${defaultUrl}?${params.toString()}`;
  } catch (e) {
    return defaultUrl;
  }
}

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
  get bugs(): string {
    return getBugReportUrl();
  },
  beer: "https://ko-fi.com/quotemyname",
} as const;
