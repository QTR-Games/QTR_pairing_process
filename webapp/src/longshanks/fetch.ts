/**
 * Getting a Longshanks event off the web and into the parser.
 *
 * The awkward part of this feature is not parsing, it is the fetch: a browser
 * can load `longshanks.org` but a WebView's `fetch` cannot, because the site
 * sends no CORS headers and the request is cross-origin. So neither packaged
 * build uses `fetch` at all. On a phone we hand the request to Capacitor's
 * native HTTP client; on desktop, to the Tauri HTTP bridge. Both run outside the
 * WebView's origin rules and simply make the GET the way a browser would. On the
 * web build (dev, tests) we fall back to `fetch`, which is enough for anything
 * same-origin and keeps this module importable in a plain Node/jsdom test --
 * though a real Longshanks import cannot work there, and no header or option
 * will change that.
 *
 * The whole thing is deliberately online-only and one-shot: the owner runs the
 * import once, the evening before an event, to seed the boards. Nothing here is
 * called again in the hall. That is why there is no caching, no retry *queue*,
 * and no background refresh -- the app's offline promise is kept by never
 * calling this at pairing time, not by making it resilient.
 *
 * There is, however, an in-flight retry, which is a different thing: Longshanks
 * refuses a minority of valid requests with a 403 and serves the same URL
 * moments later. That is not a state to persist and reconcile, it is a bad
 * second to sit through, so `withRetry` sits through it. See {@link isRetryable}
 * for what counts and what is allowed to fail immediately.
 *
 * `fetchRoster` takes an injectable `fetcher` so the URL handling and the
 * two-panel join can be tested with canned HTML. The desktop branch of
 * `fetchHtml` is testable too, through the same seam the bridge is installed
 * on; only the Capacitor branch cannot run without a device.
 */

import { Capacitor, CapacitorHttp } from "@capacitor/core";
import { getDesktopHttp } from "../desktop/platform";
import { parseRoster } from "./parse";
import type { Roster } from "./types";

/**
 * Browser-shaped request headers.
 *
 * Longshanks serves the panels to an ordinary browser without auth, so the goal
 * is only to look like one. The native client may replace some of these (the
 * platform sets its own User-Agent); they are best-effort, not load-bearing.
 */
const BROWSER_HEADERS: Record<string, string> = {
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
  "Accept-Language": "en-US,en;q=0.9",
  "Cache-Control": "no-cache",
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
};

/** A source of HTML for a URL. Swapped out in tests. */
export type HtmlFetcher = (url: string) => Promise<string>;

/**
 * A non-2xx response, carrying the status so retry can classify it.
 *
 * The status is the whole reason this is a class rather than a bare `Error`:
 * "refused this time" and "no such event" both arrive as failed requests, and
 * retrying the second one is pointless.
 */
export class LongshanksHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(describeStatus(status));
    this.name = "LongshanksHttpError";
    this.status = status;
  }
}

/**
 * What to tell the owner about a status, in their terms.
 *
 * By the time one of these surfaces the fetch has already retried, so the
 * message says so -- otherwise the advice ("try again") reads as though the
 * first attempt was the only one.
 */
function describeStatus(status: number): string {
  if (status === 403) {
    return "Longshanks refused the request (403). It does this intermittently to requests that are not a browser; the import retried and kept getting refused. Wait a moment and try again.";
  }
  if (status === 404) {
    return "Longshanks has no event with that id (404). Check the number in the event link.";
  }
  if (status === 429) {
    return "Longshanks is rate-limiting this device (429). Wait a minute and try again.";
  }
  if (status >= 500) {
    return `Longshanks is having trouble (status ${status}). This is their end, not yours -- try again shortly.`;
  }
  return `Longshanks returned status ${status}`;
}

/**
 * Backoff between attempts, in milliseconds; the length sets the retry count.
 *
 * Three retries over about four seconds. Deliberately deterministic, with no
 * jitter: jitter exists to stop many clients retrying in lockstep, and there is
 * exactly one client here -- one person, importing one event, once. Fixed delays
 * are testable, and a test that pins the schedule is worth more than randomness
 * that protects against a problem this app cannot have.
 */
const RETRY_DELAYS_MS = [400, 1200, 2500];

export interface RetryOptions {
  /** Backoff schedule; its length is how many retries happen. */
  delays?: number[];
  /** Injected in tests so a retry schedule costs no real time. */
  sleep?: (ms: number) => Promise<void>;
}

const realSleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Is this failure worth trying again?
 *
 * Longshanks intermittently answers a perfectly good request with 403 -- it is
 * bot protection reacting to a non-browser client, not a verdict about the
 * event, and the same URL succeeds moments later. That is the case this whole
 * mechanism exists for. 408/429/5xx are transient for the ordinary reasons.
 *
 * A 404 is not retried: the event genuinely is not there, and hammering it just
 * makes the owner wait four seconds to be told what we already knew. Other 4xx
 * are treated the same way.
 *
 * Anything that is not an HTTP status at all -- a dropped connection, DNS,
 * `fetch` rejecting with a TypeError -- is retried. Those are the failures most
 * likely to be a bad moment on venue wifi.
 */
export function isRetryable(error: unknown): boolean {
  if (error instanceof LongshanksHttpError) {
    const { status } = error;
    return status === 403 || status === 408 || status === 429 || status >= 500;
  }
  return true;
}

/**
 * Wrap a fetcher so transient failures are retried before they reach the user.
 *
 * Applied around whatever fetcher `fetchRoster` is given, rather than buried
 * inside {@link fetchHtml}, for two reasons: the tests inject their own fetcher
 * and would otherwise skip the retry path entirely, and the retry is a policy
 * about Longshanks rather than a property of one transport.
 */
export function withRetry(fetcher: HtmlFetcher, options: RetryOptions = {}): HtmlFetcher {
  const delays = options.delays ?? RETRY_DELAYS_MS;
  const sleep = options.sleep ?? realSleep;

  return async (url: string): Promise<string> => {
    let last: unknown;
    for (let attempt = 0; ; attempt++) {
      try {
        return await fetcher(url);
      } catch (error) {
        last = error;
        if (attempt >= delays.length || !isRetryable(error)) break;
        await sleep(delays[attempt]);
      }
    }
    throw last;
  };
}

/**
 * Pull an event id out of whatever the owner pasted.
 *
 * Accepts a bare id (`33997`) or any Longshanks URL that carries `/event/<id>/`,
 * with or without scheme or trailing slash. Anything else returns null so the UI
 * can say "that doesn't look like an event" instead of fetching a guess. It does
 * not scrape a loose number out of arbitrary text -- a wrong id would import a
 * whole wrong tournament silently.
 */
export function parseEventId(input: string): string | null {
  const s = input.trim();
  if (!s) return null;
  if (/^\d+$/.test(s)) return s;
  const m = /\/event\/(\d+)/.exec(s);
  return m ? m[1] : null;
}

/** The AJAX standings panel URL for one section of an event. */
export function panelUrl(eventId: string, section: "team" | "player"): string {
  return `https://longshanks.org/events/detail/panel_standings.php?event=${eventId}&section=${section}`;
}

/**
 * GET a URL as text, natively on device and via `fetch` on the web.
 *
 * On Android/iOS `Capacitor.getPlatform()` is not "web", so we use the native
 * HTTP client and sidestep CORS entirely. On the web we use `fetch` and surface
 * a non-2xx as an error, because a silent empty body would parse to zero teams
 * and look like a "successful" import of nothing.
 */
export async function fetchHtml(url: string): Promise<string> {
  const desktop = getDesktopHttp();
  if (desktop) {
    const { status, body } = await desktop.getText(url, BROWSER_HEADERS);
    if (status < 200 || status >= 300) {
      throw new LongshanksHttpError(status);
    }
    return body;
  }
  if (Capacitor.getPlatform() !== "web") {
    const res = await CapacitorHttp.get({ url, headers: BROWSER_HEADERS, responseType: "text" });
    if (res.status < 200 || res.status >= 300) {
      throw new LongshanksHttpError(res.status);
    }
    return typeof res.data === "string" ? res.data : String(res.data ?? "");
  }
  const res = await fetch(url, { headers: BROWSER_HEADERS });
  if (!res.ok) throw new LongshanksHttpError(res.status);
  return res.text();
}

/**
 * Fetch both standings panels for an event and parse them into a roster.
 *
 * The two panels are independent GETs, so they run together; the join happens in
 * `parseRoster`. A bad input fails fast, before any network call, with a message
 * that shows the two shapes that do work.
 *
 * Each panel is fetched through {@link withRetry}, because Longshanks refuses a
 * minority of otherwise-valid requests with a 403. Two panels fetched in
 * parallel means one import is two chances to be refused, which made a clean
 * import roughly a coin-flip on a bad morning; retrying independently per panel
 * takes that back to negligible.
 */
export async function fetchRoster(
  input: string,
  fetcher: HtmlFetcher = fetchHtml,
  options: RetryOptions = {},
): Promise<Roster> {
  const eventId = parseEventId(input);
  if (!eventId) {
    throw new Error(
      "Enter a Longshanks event id or URL, for example 33997 or https://longshanks.org/event/33997/",
    );
  }
  const get = withRetry(fetcher, options);
  const [teamHtml, playerHtml] = await Promise.all([
    get(panelUrl(eventId, "team")),
    get(panelUrl(eventId, "player")),
  ]);
  return parseRoster(teamHtml, playerHtml, eventId);
}
