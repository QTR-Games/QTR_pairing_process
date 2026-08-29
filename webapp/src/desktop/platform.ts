/**
 * A tiny platform seam for desktop-only native capability.
 *
 * The web build has no native file dialogs and no way around the browser's
 * origin rules, so these hold `null` there and each caller keeps its browser
 * behaviour. Inside the Tauri shell, `bootstrap` installs real implementations,
 * and any component can reach them through this module without importing Tauri.
 * Because nothing here depends on Tauri, it stays in the web bundle safely and
 * the actual desktop code loads only on desktop.
 */

/** Native file access the desktop shell provides; `null` on the web. */
export interface DesktopFiles {
  /**
   * Show a save dialog and write `contents` to the chosen file. Resolves to the
   * saved path, or `null` if the user cancelled.
   */
  saveBackup(contents: string, defaultName: string): Promise<string | null>;
  /**
   * Show an open dialog and read the chosen file. Resolves to its text, or
   * `null` if the user cancelled.
   */
  openBackup(): Promise<string | null>;
}

/**
 * A GET that is not subject to the webview's origin rules; `null` on the web.
 *
 * This exists for one reason: `longshanks.org` sends no CORS headers, so the
 * event importer cannot fetch it from the webview at all. The phone build
 * escapes that through Capacitor's native HTTP client, and this is the desktop
 * equivalent -- the request is made in Rust, where same-origin policy does not
 * apply. On the web build there is no escape and this stays `null`, which is
 * the honest answer: a browser tab cannot do it.
 *
 * The status comes back rather than being thrown on, so that the decision about
 * which statuses mean "retry" and which mean "give up" stays in one place, next
 * to the importer that has an opinion about it.
 */
export interface DesktopHttp {
  getText(
    url: string,
    headers: Record<string, string>,
  ): Promise<{ status: number; body: string }>;
}

/**
 * The window event a menu-driven restore announces the new boards on.
 *
 * Lives here, not in `bootstrap`, so the app can listen for it without pulling
 * the Tauri-only bootstrap code into the web bundle. `detail` is the `Board[]`
 * to render.
 */
export const BOARDS_RESTORED_EVENT = "klikklak:boards-restored";

let files: DesktopFiles | null = null;

/** Install (or clear) the desktop file bridge. Called once at desktop boot. */
export function setDesktopFiles(bridge: DesktopFiles | null): void {
  files = bridge;
}

/** The desktop file bridge, or `null` when running on the web. */
export function getDesktopFiles(): DesktopFiles | null {
  return files;
}

let http: DesktopHttp | null = null;

/** Install (or clear) the desktop HTTP bridge. Called once at desktop boot. */
export function setDesktopHttp(bridge: DesktopHttp | null): void {
  http = bridge;
}

/** The desktop HTTP bridge, or `null` when running on the web. */
export function getDesktopHttp(): DesktopHttp | null {
  return http;
}
