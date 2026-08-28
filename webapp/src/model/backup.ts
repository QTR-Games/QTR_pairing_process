/**
 * Getting boards off a phone and back onto one.
 *
 * Every board lives in `localStorage` and nowhere else. That is fine until the
 * app is reinstalled, at which point the entire history is gone -- and a
 * reinstall is not hypothetical here. The installed APK is signed with a debug
 * key that CI regenerates on every run, so Android refuses to update it in
 * place: the only way to take a new build is to uninstall the old one, and
 * uninstalling clears the storage. There is currently no way back from that.
 *
 * So this module is the seatbelt. It is deliberately independent of how the app
 * is delivered and of whether the signing key is ever fixed: a plain JSON
 * document the owner can hold somewhere the app cannot reach.
 *
 * Two design choices worth stating.
 *
 * Import merges by default rather than replacing. Restoring onto a phone that
 * already has boards must not be the second way to lose them, so a same-id
 * collision keeps whichever copy was edited more recently and anything only
 * present on one side survives. Replace exists, but it is the explicit choice.
 *
 * Import is validated with the same `isValidBoard` the normal load path uses,
 * not a second, looser check. A file that would be silently dropped on the next
 * load must be rejected at the point of import, while there is still a person
 * looking at the screen who can do something about it.
 */

import { BOARDS_KEY, isValidBoard, loadBoards, TEAM_SIZE, type Board } from "./board";
import { DEFAULTS, loadSettings, saveSettings, type Settings } from "./settings";
import { getStore } from "./store";

/**
 * Marks the file as ours, so a wrong file chosen in a hurry fails clearly.
 *
 * This is the tag written into every backup this build exports. It is *not* the
 * only tag the reader accepts -- see `READABLE_KINDS`.
 */
export const BACKUP_KIND = "klikklak.backup";

/**
 * Every tag this app has ever written, newest first.
 *
 * Renaming the tag is cosmetic on its own; what makes the rename safe is that
 * the reader never narrowed. A backup is the thing you reach for on the morning
 * something has gone wrong, and a reader that refuses a file it wrote last year
 * because the product was renamed in between has failed at its only job.
 *
 * So the writer moves forward and the reader stays permissive: anything in this
 * list is accepted, and `parseBackup` normalises what it returns to
 * `BACKUP_KIND`, so nothing downstream has to know which vintage it came from.
 * Add to this list, never remove from it.
 */
const READABLE_KINDS: readonly string[] = [BACKUP_KIND, "qtr.pairing.backup"];

/** Bumped only for a shape change that an older reader could misread. */
export const BACKUP_VERSION = 1;

export interface Backup {
  kind: typeof BACKUP_KIND;
  version: number;
  exportedAt: number;
  teamSize: number;
  boards: Board[];
  settings: Settings;
}

/** How an incoming file should meet what is already stored. */
export type ImportMode = "merge" | "replace";

export interface ImportResult {
  boards: Board[];
  settings: Settings;
  added: number;
  updated: number;
  skipped: number;
}

/** Everything worth keeping, as a plain object. */
export function buildBackup(): Backup {
  return {
    kind: BACKUP_KIND,
    version: BACKUP_VERSION,
    exportedAt: Date.now(),
    teamSize: TEAM_SIZE,
    boards: loadBoards(),
    settings: loadSettings(),
  };
}

/**
 * The backup as text.
 *
 * Indented on purpose. This is a file a person may end up opening in a text
 * editor to check their players are in it, and that reassurance is worth more
 * than the bytes.
 */
export const serializeBackup = (backup: Backup = buildBackup()): string =>
  JSON.stringify(backup, null, 2);

/** A filename that sorts by date and does not collide across a weekend. */
export function backupFilename(at: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const stamp =
    `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}` +
    `-${pad(at.getHours())}${pad(at.getMinutes())}`;
  return `klikklak-boards-${stamp}.json`;
}

export class BackupError extends Error {}

/**
 * Read a backup from text.
 *
 * Throws `BackupError` with something a person can act on, because the only
 * place this is called is a screen where someone just chose a file and needs to
 * know whether it worked.
 */
export function parseBackup(text: string): Backup {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new BackupError("That is not a backup file -- it is not valid JSON.");
  }

  const b = parsed as Partial<Backup>;
  if (!b || typeof b !== "object") {
    throw new BackupError("That file does not contain a backup.");
  }
  if (typeof b.kind !== "string" || !READABLE_KINDS.includes(b.kind)) {
    throw new BackupError("That file is not a KLIK KLAK backup.");
  }
  if (typeof b.version !== "number" || b.version > BACKUP_VERSION) {
    throw new BackupError(
      `That backup was written by a newer version of the app (format ${String(b.version)}).`,
    );
  }
  if (!Array.isArray(b.boards)) {
    throw new BackupError("That backup has no boards in it.");
  }

  // A team-size change would silently reshape every matrix, so refuse rather
  // than import something this build cannot represent.
  if (typeof b.teamSize === "number" && b.teamSize !== TEAM_SIZE) {
    throw new BackupError(
      `That backup is for ${b.teamSize}-player teams; this app is set up for ${TEAM_SIZE}.`,
    );
  }

  return {
    kind: BACKUP_KIND,
    version: b.version,
    exportedAt: typeof b.exportedAt === "number" ? b.exportedAt : 0,
    teamSize: TEAM_SIZE,
    boards: b.boards.filter(isValidBoard),
    settings: isSettings(b.settings) ? b.settings : { ...DEFAULTS },
  };
}

const isSettings = (v: unknown): v is Settings =>
  !!v && typeof v === "object" && typeof (v as Settings).dodgeMode === "string";

/**
 * Fold a parsed backup into what is already stored, and persist the result.
 *
 * `skipped` counts boards the file offered that were not taken because the
 * stored copy was the same age or newer. It is reported rather than hidden so
 * the screen can say "nothing changed" honestly instead of implying a restore
 * happened when it did not.
 */
export function applyBackup(backup: Backup, mode: ImportMode = "merge"): ImportResult {
  const existing = mode === "replace" ? [] : loadBoards();
  const byId = new Map(existing.map((b) => [b.id, b]));

  let added = 0;
  let updated = 0;
  let skipped = 0;

  for (const incoming of backup.boards) {
    const current = byId.get(incoming.id);
    if (!current) {
      byId.set(incoming.id, incoming);
      added++;
      continue;
    }
    // Undated boards are treated as oldest, so a real timestamp always wins.
    if ((incoming.updatedAt ?? 0) > (current.updatedAt ?? 0)) {
      byId.set(incoming.id, incoming);
      updated++;
    } else {
      skipped++;
    }
  }

  const boards = [...byId.values()].sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0));
  writeBoards(boards);

  // Only adopt settings on a replace. A merge is about rescuing boards, and
  // silently changing how much the screen says is not what was asked for.
  const settings = mode === "replace" ? saveSettings(backup.settings) : loadSettings();

  return { boards, settings, added, updated, skipped };
}

/**
 * Written here rather than looping `saveBoard`, which stamps `updatedAt` on
 * every write and would destroy the very timestamps the merge just used.
 */
function writeBoards(boards: Board[]): void {
  try {
    getStore().setItem(BOARDS_KEY, JSON.stringify(boards));
  } catch {
    throw new BackupError("There was not enough room on the device to save the restored boards.");
  }
}
