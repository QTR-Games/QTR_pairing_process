/**
 * The desktop backend for the storage seam: a synchronous key-value face over
 * an asynchronous SQLite database.
 *
 * The model reads and writes boards synchronously (see `store.ts`), but a real
 * database call is a promise. The reconciliation the seam's own doc calls for is
 * done here: at startup every `key -> JSON` row is hydrated into an in-memory
 * mirror, so `getItem` answers from memory with no await; `setItem`/`removeItem`
 * update the mirror synchronously and then *write through* to the database on a
 * serialized queue, so rows land in the order the model issued them.
 *
 * The one honest compromise this makes with the seam contract: `setItem` cannot
 * throw on a disk-full error, because the failure happens later, off the queue.
 * Instead of silently dropping the write (which the seam doc forbids), the value
 * stays in the mirror -- so the round in progress survives exactly as it would
 * on a swallowed `localStorage` quota error -- and the failure is reported to
 * `onError` for the host to log. `flush()` lets a caller (a test, or a clean
 * shutdown) await the queue and observe those failures.
 *
 * This module is deliberately free of any Tauri import: it depends only on the
 * small async `KvDatabase` port, so it runs and is unit-tested in plain Node.
 * The Tauri wiring that supplies a real SQLite-backed `KvDatabase` lives in
 * `desktop/bootstrap.ts`.
 */
import type { KeyValueStore } from "./store";

/** The async persistence the mirror writes through to. */
export interface KvDatabase {
  put(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

/** Where a failed write-through is reported. The value stays in the mirror. */
export type KvErrorHandler = (
  error: unknown,
  op: { type: "put" | "remove"; key: string },
) => void;

export interface MemoryMirrorStore {
  /** The synchronous store to hand to `setStore`. */
  store: KeyValueStore;
  /** Resolve once every write enqueued so far has been persisted or failed. */
  flush(): Promise<void>;
}

/**
 * Build a synchronous {@link KeyValueStore} backed by an in-memory mirror of
 * `rows` that writes through to `db`.
 */
export function createMemoryMirrorStore(
  rows: Iterable<readonly [string, string]>,
  db: KvDatabase,
  onError?: KvErrorHandler,
): MemoryMirrorStore {
  const mirror = new Map<string, string>();
  for (const [key, value] of rows) mirror.set(key, value);

  // A single serialized chain: each write waits for the previous one, so the
  // database ends up in the same order the model wrote, and one slow write
  // never races ahead of a later one for the same key.
  let tail: Promise<void> = Promise.resolve();
  const enqueue = (
    run: () => Promise<void>,
    op: { type: "put" | "remove"; key: string },
  ): void => {
    tail = tail.then(run).catch((error) => onError?.(error, op));
  };

  const store: KeyValueStore = {
    // has()-check, not `?? null`: an empty string is a legitimate stored value.
    getItem: (key) => (mirror.has(key) ? (mirror.get(key) as string) : null),
    setItem: (key, value) => {
      mirror.set(key, value);
      enqueue(() => db.put(key, value), { type: "put", key });
    },
    removeItem: (key) => {
      mirror.delete(key);
      enqueue(() => db.remove(key), { type: "remove", key });
    },
  };

  return { store, flush: () => tail };
}

/**
 * The one-time migration source for a fresh desktop database: every `qtr.*` row
 * a prior web, PWA or webview run left behind in `localStorage`.
 *
 * Returned as `[key, value]` pairs so the caller can seed SQLite on first launch
 * and an upgrading user keeps their boards, live round and settings. Kept pure
 * (it takes any `Storage`-shaped object) so it is testable without a browser.
 */
export function collectLegacyRows(
  storage: Pick<Storage, "length" | "key" | "getItem">,
): Array<[string, string]> {
  const rows: Array<[string, string]> = [];
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (key === null || !key.startsWith("qtr.")) continue;
    const value = storage.getItem(key);
    if (value !== null) rows.push([key, value]);
  }
  return rows;
}
