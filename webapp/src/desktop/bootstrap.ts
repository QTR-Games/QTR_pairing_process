/**
 * Desktop startup: point the storage seam at SQLite before the first board read.
 *
 * On the web this file's work never runs -- {@link isDesktop} is false and the
 * seam keeps its default `localStorage` backend. Inside the Tauri shell it opens
 * (or creates) a SQLite database in the app's data directory, ensures the
 * `key -> JSON` table exists, seeds it once from any legacy `localStorage` rows,
 * hydrates every row into an in-memory mirror, and installs that mirror through
 * `setStore`. The reconciliation of the model's synchronous reads with async
 * SQLite lives in `sqliteStore.ts`; this file is only the Tauri wiring.
 */
import Database from "@tauri-apps/plugin-sql";
import { setStore } from "../model/store";
import {
  collectLegacyRows,
  createMemoryMirrorStore,
  type KvDatabase,
} from "../model/sqliteStore";

/** The database file, resolved by the SQL plugin under the app data dir. */
const DB_URL = "sqlite:klikklak.db";
const KV_TABLE = "kv";
const CREATE_KV = `CREATE TABLE IF NOT EXISTS ${KV_TABLE} (key TEXT PRIMARY KEY, value TEXT NOT NULL)`;
const UPSERT_KV = `INSERT INTO ${KV_TABLE} (key, value) VALUES ($1, $2) ON CONFLICT(key) DO UPDATE SET value = excluded.value`;
const DELETE_KV = `DELETE FROM ${KV_TABLE} WHERE key = $1`;

/** True only inside the Tauri desktop shell, where the SQL plugin is available. */
export function isDesktop(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window)
  );
}

/**
 * Open the desktop SQLite store and install it on the seam.
 *
 * Throws if the database cannot be opened; the caller falls back to the default
 * `localStorage` backend so the app still launches.
 */
export async function initDesktopStore(): Promise<void> {
  const db = await Database.load(DB_URL);
  await db.execute(CREATE_KV);
  await seedFromLegacy(db);

  const rows = await db.select<Array<{ key: string; value: string }>>(
    `SELECT key, value FROM ${KV_TABLE}`,
  );

  const port: KvDatabase = {
    put: async (key, value) => {
      await db.execute(UPSERT_KV, [key, value]);
    },
    remove: async (key) => {
      await db.execute(DELETE_KV, [key]);
    },
  };

  const { store } = createMemoryMirrorStore(
    rows.map((row) => [row.key, row.value] as [string, string]),
    port,
    (error, op) =>
      console.error(`kv ${op.type} failed for "${op.key}"`, error),
  );
  setStore(store);
}

/**
 * On the first launch after upgrade the `kv` table is empty; carry over any
 * `qtr.*` rows a previous web/PWA run left in this webview's `localStorage` so
 * the user's boards survive the move to SQLite. A no-op on every later launch.
 */
async function seedFromLegacy(db: {
  select<T>(query: string): Promise<T>;
  execute(query: string, bindValues?: unknown[]): Promise<unknown>;
}): Promise<void> {
  const counted = await db.select<Array<{ n: number }>>(
    `SELECT COUNT(*) AS n FROM ${KV_TABLE}`,
  );
  const isEmpty = (counted[0]?.n ?? 0) === 0;
  if (!isEmpty || typeof localStorage === "undefined") return;

  for (const [key, value] of collectLegacyRows(localStorage)) {
    await db.execute(UPSERT_KV, [key, value]);
  }
}
