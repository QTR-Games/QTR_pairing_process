/**
 * The desktop file bridge: native save/open dialogs over two Tauri commands.
 *
 * Kept apart from {@link ./platform} so the Tauri import lives only in the
 * desktop bootstrap chunk and never reaches the web bundle. The dialog and the
 * disk access happen in Rust (`save_backup` / `open_backup`); this is the thin
 * JavaScript side that forwards to them.
 */
import { invoke } from "@tauri-apps/api/core";
import type { DesktopFiles } from "./platform";

/** The shape of Tauri's `invoke` we depend on -- narrowed so tests can fake it. */
type Invoke = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;

/**
 * Build a {@link DesktopFiles} over an `invoke` function. The default is Tauri's
 * real `invoke`; tests pass a fake so this stays unit-testable off a device.
 */
export function createDesktopFiles(invokeFn: Invoke = invoke): DesktopFiles {
  return {
    saveBackup: (contents, defaultName) =>
      invokeFn<string | null>("save_backup", { contents, defaultName }),
    openBackup: () => invokeFn<string | null>("open_backup"),
  };
}
