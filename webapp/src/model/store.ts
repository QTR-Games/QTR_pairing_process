/**
 * The one place the model talks to storage.
 *
 * Every board, live round and setting reaches persistence through this
 * key-value seam, and nothing else in the model touches `localStorage`
 * directly. On the web and on a phone the seam is a thin proxy over
 * `localStorage`, so behaviour is byte-for-byte what it has always been. On the
 * desktop build the same seam is pointed at a SQLite-backed store instead: a
 * table of `key -> JSON string` rows, which is exactly the shape the values
 * already have -- every value written through here is a JSON string stored
 * under a stable key (`qtr.boards.v1`, `qtr.live.v2`, `qtr.settings.v1`).
 *
 * The interface is deliberately the subset of the DOM `Storage` API the model
 * actually uses -- `getItem`, `setItem`, `removeItem` -- and it stays
 * synchronous. The existing readers and writers are synchronous, so a backend
 * swap must present the same synchronous face: a desktop store hydrates its
 * rows into memory at startup and writes through to SQLite, rather than turning
 * every board read into a promise the UI would have to await.
 *
 * Two rules a replacement backend must honour, because the rest of the model
 * relies on them:
 *  - `getItem` returns the stored string or `null`, and may throw; every reader
 *    already wraps it and falls back to empty/defaults on failure.
 *  - `setItem` throws when it cannot store (a full disk, exhausted quota). The
 *    callers depend on that throw -- some swallow it to keep the in-memory round
 *    alive, and the backup writer turns it into a message a person can act on.
 *    A backend that silently drops writes would make those paths lie.
 */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * The default backend: the browser's own `localStorage`.
 *
 * A direct delegation on purpose. The methods are looked up at call time, not
 * at module load, so simply importing the model never touches `localStorage`;
 * and because nothing here catches, the behaviour a caller sees -- the value,
 * the `null`, or the quota error -- is identical to calling `localStorage`
 * itself, which is what every reader and writer was written against.
 */
export const localStorageStore: KeyValueStore = {
  getItem: (key) => localStorage.getItem(key),
  setItem: (key, value) => localStorage.setItem(key, value),
  removeItem: (key) => localStorage.removeItem(key),
};

let active: KeyValueStore = localStorageStore;

/** The store the model currently persists through. */
export function getStore(): KeyValueStore {
  return active;
}

/**
 * Point the model at a different backend.
 *
 * Called once at startup by a host that has somewhere other than
 * `localStorage` to keep data -- the desktop shell swaps in its SQLite-backed
 * store here before the first board is read.
 */
export function setStore(store: KeyValueStore): void {
  active = store;
}

/** Restore the default `localStorage` backend. Primarily for tests. */
export function resetStore(): void {
  active = localStorageStore;
}
