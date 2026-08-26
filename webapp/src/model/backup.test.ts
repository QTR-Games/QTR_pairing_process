/**
 * Backup is the one feature whose failure mode is silent and permanent, so it
 * is tested against the cases that actually happen: the wrong file, a truncated
 * file, a file from a future version, and -- the important one -- restoring
 * onto a phone that is not empty.
 *
 * These run against a stubbed storage rather than a real one, following the
 * pattern the other model tests use: vitest runs in node, so `localStorage` has
 * to exist before the module under test is imported.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

class MemoryStorage {
  private map = new Map<string, string>();
  getItem = (k: string) => this.map.get(k) ?? null;
  setItem = (k: string, v: string) => void this.map.set(k, v);
  removeItem = (k: string) => void this.map.delete(k);
  clear = () => this.map.clear();
  key = (i: number) => [...this.map.keys()][i] ?? null;
  get length() {
    return this.map.size;
  }
}

const storage = new MemoryStorage();
vi.stubGlobal("localStorage", storage);

const backup = await import("./backup");
const boardModel = await import("./board");

const {
  BACKUP_KIND,
  BACKUP_VERSION,
  BackupError,
  applyBackup,
  backupFilename,
  buildBackup,
  parseBackup,
  serializeBackup,
} = backup;
const { BOARDS_KEY, emptyBoard } = boardModel;

/** A board that passes `isValidBoard`, with the fields the merge cares about. */
function board(id: string, opponent: string, updatedAt: number) {
  return { ...emptyBoard(), id, opponent, updatedAt };
}

const write = (boards: unknown[]) => storage.setItem(BOARDS_KEY, JSON.stringify(boards));
const read = () => JSON.parse(storage.getItem(BOARDS_KEY) ?? "[]");

beforeEach(() => storage.clear());

describe("a backup survives the round trip", () => {
  it("carries every board back out again", () => {
    write([board("a", "Sweden", 100), board("b", "Poland", 200)]);

    const restored = parseBackup(serializeBackup());

    expect(restored.boards.map((b) => b.opponent).sort()).toEqual(["Poland", "Sweden"]);
    expect(restored.kind).toBe(BACKUP_KIND);
    expect(restored.version).toBe(BACKUP_VERSION);
  });

  it("is indented, because someone will open it to check their players are there", () => {
    write([board("a", "Sweden", 100)]);
    expect(serializeBackup()).toContain("\n  ");
  });

  it("exports an empty device without complaining", () => {
    expect(buildBackup().boards).toEqual([]);
    expect(() => parseBackup(serializeBackup())).not.toThrow();
  });
});

describe("the tag on the file", () => {
  /*
   * The app was renamed from QTR Pairing to KLIK KLAK. The writer moved to the
   * new tag; the reader must not, or a file exported before the rename becomes
   * unreadable by the app that wrote it.
   */
  it("writes the current name, not the old one", () => {
    expect(BACKUP_KIND).toBe("klikklak.backup");
    write([board("a", "Sweden", 100)]);
    expect(serializeBackup()).toContain('"kind": "klikklak.backup"');
  });

  it("still reads a backup written before the rename", () => {
    const legacy = JSON.stringify({
      kind: "qtr.pairing.backup",
      version: BACKUP_VERSION,
      teamSize: 5,
      boards: [board("a", "Sweden", 100)],
    });

    const restored = parseBackup(legacy);

    expect(restored.boards.map((b) => b.opponent)).toEqual(["Sweden"]);
  });

  it("hands back the current tag whatever vintage went in, so callers need not care", () => {
    const legacy = JSON.stringify({
      kind: "qtr.pairing.backup",
      version: BACKUP_VERSION,
      boards: [],
    });

    expect(parseBackup(legacy).kind).toBe(BACKUP_KIND);
  });

  it("still refuses a tag it has never written", () => {
    const alien = JSON.stringify({
      kind: "some.other.app.backup",
      version: BACKUP_VERSION,
      boards: [],
    });

    expect(() => parseBackup(alien)).toThrow(/not a KLIK KLAK backup/);
  });
});

describe("a bad file fails where someone can see it", () => {
  it("rejects text that is not JSON", () => {
    expect(() => parseBackup("not a file")).toThrow(BackupError);
  });

  it("rejects a JSON file that is not ours", () => {
    expect(() => parseBackup('{"hello":"world"}')).toThrow(/not a KLIK KLAK backup/);
  });

  it("rejects a backup from a newer app", () => {
    const future = JSON.stringify({
      kind: BACKUP_KIND,
      version: BACKUP_VERSION + 1,
      boards: [],
    });
    expect(() => parseBackup(future)).toThrow(/newer version/);
  });

  it("refuses a backup written for a different team size", () => {
    const other = JSON.stringify({
      kind: BACKUP_KIND,
      version: BACKUP_VERSION,
      teamSize: 3,
      boards: [],
    });
    expect(() => parseBackup(other)).toThrow(/3-player teams/);
  });

  it("drops individual boards that would not survive a normal load", () => {
    const mixed = JSON.stringify({
      kind: BACKUP_KIND,
      version: BACKUP_VERSION,
      boards: [board("good", "Sweden", 1), { id: "bad", fractions: [[0.5]] }],
    });
    expect(parseBackup(mixed).boards.map((b) => b.id)).toEqual(["good"]);
  });
});

describe("restoring onto a phone that already has boards", () => {
  it("adds what is missing and leaves the rest alone", () => {
    write([board("a", "Sweden", 100)]);
    const incoming = parseBackup(
      JSON.stringify({
        kind: BACKUP_KIND,
        version: BACKUP_VERSION,
        boards: [board("b", "Poland", 50)],
      }),
    );

    const result = applyBackup(incoming, "merge");

    expect(result.added).toBe(1);
    expect(result.updated).toBe(0);
    expect(read().map((b: { id: string }) => b.id).sort()).toEqual(["a", "b"]);
  });

  it("keeps the copy that was edited more recently", () => {
    write([board("a", "Stale name", 100)]);
    const incoming = parseBackup(
      JSON.stringify({
        kind: BACKUP_KIND,
        version: BACKUP_VERSION,
        boards: [board("a", "Newer name", 500)],
      }),
    );

    const result = applyBackup(incoming, "merge");

    expect(result.updated).toBe(1);
    expect(read()[0].opponent).toBe("Newer name");
  });

  it("does not overwrite a board that is newer on the device", () => {
    write([board("a", "Edited here", 900)]);
    const incoming = parseBackup(
      JSON.stringify({
        kind: BACKUP_KIND,
        version: BACKUP_VERSION,
        boards: [board("a", "Older backup", 100)],
      }),
    );

    const result = applyBackup(incoming, "merge");

    expect(result.skipped).toBe(1);
    expect(result.updated).toBe(0);
    expect(read()[0].opponent).toBe("Edited here");
  });

  it("preserves the timestamps it just used to decide", () => {
    write([board("a", "Sweden", 100)]);
    const incoming = parseBackup(
      JSON.stringify({
        kind: BACKUP_KIND,
        version: BACKUP_VERSION,
        boards: [board("b", "Poland", 50)],
      }),
    );

    applyBackup(incoming, "merge");

    const stored = read() as { id: string; updatedAt: number }[];
    expect(stored.find((b) => b.id === "a")!.updatedAt).toBe(100);
    expect(stored.find((b) => b.id === "b")!.updatedAt).toBe(50);
  });

  it("replaces everything only when asked to", () => {
    write([board("a", "Sweden", 100)]);
    const incoming = parseBackup(
      JSON.stringify({
        kind: BACKUP_KIND,
        version: BACKUP_VERSION,
        boards: [board("b", "Poland", 50)],
      }),
    );

    applyBackup(incoming, "replace");

    expect(read().map((b: { id: string }) => b.id)).toEqual(["b"]);
  });

  it("is safe to run twice", () => {
    write([board("a", "Sweden", 100)]);
    const incoming = parseBackup(serializeBackup());

    applyBackup(incoming, "merge");
    const second = applyBackup(incoming, "merge");

    expect(second.added).toBe(0);
    expect(second.updated).toBe(0);
    expect(second.skipped).toBe(1);
    expect(read()).toHaveLength(1);
  });
});

describe("the filename", () => {
  it("sorts by date and names the app", () => {
    const name = backupFilename(new Date(2026, 7, 31, 9, 5));
    expect(name).toBe("klikklak-boards-2026-08-31-0905.json");
  });
});
