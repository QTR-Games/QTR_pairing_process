/**
 * The desktop HTTP bridge: a GET that is not bound by the webview's origin rules.
 *
 * Kept apart from {@link ./platform} so the Tauri import lives only in the
 * desktop bootstrap chunk and never reaches the web bundle -- the same split the
 * file bridge uses next door in `files.ts`.
 *
 * The plugin's `fetch` is deliberately shaped like the Web API, so this wrapper
 * is thin. What it adds is the narrowing: the importer wants a status and a body,
 * and does not want to hold a `Response` whose second `.text()` would throw. Any
 * opinion about which statuses are worth retrying stays with the importer.
 */
import { fetch as tauriFetch } from "@tauri-apps/plugin-http";
import type { DesktopHttp } from "./platform";

/**
 * The slice of `fetch` we depend on -- narrowed so tests can fake it without
 * standing up a Tauri runtime, matching how `createDesktopFiles` takes `invoke`.
 */
export type FetchLike = (
  url: string,
  init: { method: string; headers: Record<string, string> },
) => Promise<{ status: number; text(): Promise<string> }>;

/** Build a {@link DesktopHttp} over a fetch function; the default is Tauri's. */
export function createDesktopHttp(fetchFn: FetchLike = tauriFetch as FetchLike): DesktopHttp {
  return {
    async getText(url, headers) {
      const res = await fetchFn(url, { method: "GET", headers });
      return { status: res.status, body: await res.text() };
    },
  };
}
