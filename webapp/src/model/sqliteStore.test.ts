import { describe, expect, it, vi } from "vitest";
import {
  collectLegacyRows,
  createMemoryMirrorStore,
  type KvDatabase,
} from "./sqliteStore";

/** An in-memory stand-in for the SQLite port, with optional failure injection. */
function fakeDb(): KvDatabase & {
  rows: Map<string, string>;
  failNextPut?: unknown;
} {
  const rows = new Map<string, string>();
  const db = {
    rows,
    failNextPut: undefined as unknown,
    put: async (key: string, value: string) => {
      if (db.failNextPut !== undefined) {
        const err = db.failNextPut;
        db.failNextPut = undefined;
        throw err;
      }
      rows.set(key, value);
    },
    remove: async (key: string) => {
      rows.delete(key);
    },
  };
  return db;
}

describe("createMemoryMirrorStore", () => {
  it("answers reads from the hydrated mirror, synchronously", () => {
    const { store } = createMemoryMirrorStore(
      [
        ["qtr.boards.v1", "[1,2]"],
        ["qtr.empty", ""],
      ],
      fakeDb(),
    );

    expect(store.getItem("qtr.boards.v1")).toBe("[1,2]");
    // an empty string is a real stored value, not a miss
    expect(store.getItem("qtr.empty")).toBe("");
    expect(store.getItem("qtr.missing")).toBeNull();
  });

  it("makes a write visible immediately and persists it through", async () => {
    const db = fakeDb();
    const { store, flush } = createMemoryMirrorStore([], db);

    store.setItem("qtr.live.v2", "{}");
    // visible before the async write-through has run
    expect(store.getItem("qtr.live.v2")).toBe("{}");
    expect(db.rows.has("qtr.live.v2")).toBe(false);

    await flush();
    expect(db.rows.get("qtr.live.v2")).toBe("{}");
  });

  it("removes from the mirror and the database", async () => {
    const db = fakeDb();
    // the row already lives in the database and is hydrated into the mirror
    db.rows.set("qtr.settings.v1", "{}");
    const { store, flush } = createMemoryMirrorStore(
      [["qtr.settings.v1", "{}"]],
      db,
    );
    expect(db.rows.has("qtr.settings.v1")).toBe(true);

    store.removeItem("qtr.settings.v1");
    expect(store.getItem("qtr.settings.v1")).toBeNull();

    await flush();
    expect(db.rows.has("qtr.settings.v1")).toBe(false);
  });

  it("persists writes in the order they were issued", async () => {
    const db = fakeDb();
    const { store, flush } = createMemoryMirrorStore([], db);

    store.setItem("k", "1");
    store.setItem("k", "2");
    store.setItem("k", "3");

    await flush();
    expect(db.rows.get("k")).toBe("3");
  });

  it("keeps the value in memory and reports when a write-through fails", async () => {
    const db = fakeDb();
    const onError = vi.fn();
    const { store, flush } = createMemoryMirrorStore([], db, onError);

    db.failNextPut = new Error("disk full");
    store.setItem("qtr.boards.v1", "[]");

    // the round in progress still sees its data despite the failed persist
    expect(store.getItem("qtr.boards.v1")).toBe("[]");

    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][1]).toEqual({
      type: "put",
      key: "qtr.boards.v1",
    });
    // the failure did not tear down the queue: later writes still land
    store.setItem("qtr.boards.v1", "[7]");
    await flush();
    expect(db.rows.get("qtr.boards.v1")).toBe("[7]");
  });
});

describe("collectLegacyRows", () => {
  function storageOf(entries: Record<string, string>): Storage {
    const keys = Object.keys(entries);
    return {
      length: keys.length,
      key: (i: number) => keys[i] ?? null,
      getItem: (k: string) => (k in entries ? entries[k] : null),
      setItem: () => {},
      removeItem: () => {},
      clear: () => {},
    } as unknown as Storage;
  }

  it("collects only qtr.* rows and leaves everything else behind", () => {
    const rows = collectLegacyRows(
      storageOf({
        "qtr.boards.v1": "[1]",
        "qtr.settings.v1": "{}",
        "unrelated.key": "x",
        theme: "dark",
      }),
    );

    expect(new Map(rows)).toEqual(
      new Map([
        ["qtr.boards.v1", "[1]"],
        ["qtr.settings.v1", "{}"],
      ]),
    );
  });

  it("returns nothing when there is no legacy data", () => {
    expect(collectLegacyRows(storageOf({ theme: "dark" }))).toEqual([]);
  });
});
