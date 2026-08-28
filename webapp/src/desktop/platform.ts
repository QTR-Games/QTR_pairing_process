/**
 * A tiny platform seam for desktop-only native file access.
 *
 * The web build has no native file dialogs, so this holds `null` there and the
 * backup screen keeps its browser behaviour -- a download and a file input.
 * Inside the Tauri shell, `bootstrap` installs a real implementation backed by
 * native save/open dialogs, and any component can reach it through this module
 * without importing Tauri. Because nothing here depends on Tauri, it stays in
 * the web bundle safely and the actual desktop code loads only on desktop.
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
