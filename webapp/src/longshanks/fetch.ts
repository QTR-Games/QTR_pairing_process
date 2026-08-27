/**
 * Getting a Longshanks event off the web and into the parser.
 *
 * The awkward part of this feature is not parsing, it is the fetch: a browser
 * can load `longshanks.org` but a WebView's `fetch` cannot, because the site
 * sends no CORS headers and the request is cross-origin. So on a real device we
 * do not use `fetch` at all -- we hand the request to Capacitor's native HTTP
 * client, which runs outside the WebView's origin rules and simply makes the
 * GET the way a browser would. On the web build (dev, tests) we fall back to
 * `fetch`, which is enough for anything same-origin and keeps this module
 * importable in a plain Node/jsdom test.
 *
 * The whole thing is deliberately online-only and one-shot: the owner runs the
 * import once, the evening before an event, to seed the boards. Nothing here is
 * called again in the hall. That is why there is no caching, retry queue, or
 * background refresh -- the app's offline promise is kept by never calling this
 * at pairing time, not by making it resilient.
 *
 * `fetchRoster` takes an injectable `fetcher` so the URL handling and the
 * two-panel join can be tested with canned HTML, leaving only the tiny native/
 * web branch untested (it cannot run without a device).
 */

import { Capacitor, CapacitorHttp } from "@capacitor/core";
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
  if (Capacitor.getPlatform() !== "web") {
    const res = await CapacitorHttp.get({ url, headers: BROWSER_HEADERS, responseType: "text" });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`Longshanks returned status ${res.status}`);
    }
    return typeof res.data === "string" ? res.data : String(res.data ?? "");
  }
  const res = await fetch(url, { headers: BROWSER_HEADERS });
  if (!res.ok) throw new Error(`Longshanks returned status ${res.status}`);
  return res.text();
}

/**
 * Fetch both standings panels for an event and parse them into a roster.
 *
 * The two panels are independent GETs, so they run together; the join happens in
 * `parseRoster`. A bad input fails fast, before any network call, with a message
 * that shows the two shapes that do work.
 */
export async function fetchRoster(input: string, fetcher: HtmlFetcher = fetchHtml): Promise<Roster> {
  const eventId = parseEventId(input);
  if (!eventId) {
    throw new Error(
      "Enter a Longshanks event id or URL, for example 33997 or https://longshanks.org/event/33997/",
    );
  }
  const [teamHtml, playerHtml] = await Promise.all([
    fetcher(panelUrl(eventId, "team")),
    fetcher(panelUrl(eventId, "player")),
  ]);
  return parseRoster(teamHtml, playerHtml, eventId);
}
