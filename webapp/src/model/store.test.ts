/*
 * The storage seam every board, round and setting now passes through.
 *
 * Like the other model tests, Vitest runs in the node environment here, so
 * there is no `localStorage`. The same small stub convention is used: a
 * `MemoryStorage` is installed as the global `localStorage`, which is exactly
 * what the default backend delegates to. That lets these tests prove both that
 * the default still writes through to the real global, and that injecting
 * another backend diverts every write away from it while keeping the keys
 * identical.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { Board } from "./board";

class MemoryStorage {
  private map = new Map<string, string>();
  getItem(k: string) {
    return this.map.has(k) ? this.map.get(k)! : null;
  }
  setItem(k: string, v: string) {
    this.map.set(k, String(v));
  }
  removeItem(k: string) {
    this.map.delete(k);
  }
  clear() {
    this.map.clear();
  }
}

const globalStorage = new MemoryStorage();
(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = globalStorage;

// Imported after the global stub is installed, matching the other model tests.
const { BOARDS_KEY, loadBoards, saveBoard } = await import("./board");
const { loadSettings, saveSettings } = await import("./settings");
const { getStore, localStorageStore, resetStore, setStore } = await import("./store");

/** A stand-in backend that keeps everything in a plain Map, like a desktop store would. */
function memoryStore() {
  const map = new Map<string, string>();
  return {
    map,
    getItem: (key: string) => (map.has(key) ? (map.get(key) as string) : null),
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
  };
}

const sampleBoard = (id: string): Board => ({
  id,
  opponent: "Test",
  ourPlayers: ["a", "b", "c", "d", "e"],
  theirPlayers: ["v", "w", "x", "y", "z"],
  fractions: Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => 0.5)),
  scaleId: "pct",
  ourTeamFirst: true,
  updatedAt: 1,
});

beforeEach(() => globalStorage.clear());
afterEach(() => resetStore());

describe("store seam", () => {
  it("defaults to the localStorage backend", () => {
    expect(getStore()).toBe(localStorageStore);
  });

  it("the default backend reads and writes the global localStorage", () => {
    getStore().setItem("qtr.probe", "hello");
    expect(globalStorage.getItem("qtr.probe")).toBe("hello");
    expect(getStore().getItem("qtr.probe")).toBe("hello");
    getStore().removeItem("qtr.probe");
    expect(globalStorage.getItem("qtr.probe")).toBeNull();
  });

  it("routes board persistence through an injected backend, keys untouched", () => {
    const mem = memoryStore();
    setStore(mem);

    saveBoard(sampleBoard("b1"));

    // Nothing leaked to the localStorage backend...
    expect(globalStorage.getItem(BOARDS_KEY)).toBeNull();
    // ...and the injected store holds the data under the exact same key.
    expect(mem.map.has(BOARDS_KEY)).toBe(true);
    expect(loadBoards().map((b) => b.id)).toEqual(["b1"]);
  });

  it("routes settings persistence through an injected backend", () => {
    const mem = memoryStore();
    setStore(mem);

    saveSettings({ ...loadSettings(), dodgeMode: "always" });

    expect(globalStorage.getItem("qtr.settings.v1")).toBeNull();
    expect(mem.map.has("qtr.settings.v1")).toBe(true);
    expect(loadSettings().dodgeMode).toBe("always");
  });

  it("resetStore restores the localStorage backend", () => {
    setStore(memoryStore());
    expect(getStore()).not.toBe(localStorageStore);
    resetStore();
    expect(getStore()).toBe(localStorageStore);
  });
});
