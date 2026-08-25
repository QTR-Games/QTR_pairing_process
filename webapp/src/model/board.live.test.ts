/*
 * The round has to survive a reload.
 *
 * This is not a hypothetical. Android reclaims backgrounded tabs, screens get
 * tapped awake into a fresh load, and as of `main.tsx` a new build deliberately
 * reloads the page the moment it is ready. Each of those used to cost a round in
 * progress. These tests are what stop that regressing.
 *
 * Vitest runs in the node environment here, so there is no `localStorage`. A
 * small stub is cheaper and less fragile than adding jsdom to the toolchain for
 * four functions.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { newRound, type LiveState } from "../engine/live";

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

const store = new MemoryStorage();
(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = store;

// Imported after the stub is installed, since the module reads storage on call.
const { loadLive, saveLive } = await import("./board");

describe("the round in progress survives a reload", () => {
  beforeEach(() => store.clear());

  it("comes back exactly as it was left", () => {
    const state: LiveState = {
      ...newRound(5, true),
      attacker: 2,
      attackerSide: "their",
      banked: 7,
      committed: [
        { ours: 0, theirs: 3, value: 4 },
        { ours: 1, theirs: 4, value: 3 },
      ],
    };

    saveLive("board-a", state);
    const back = loadLive("board-a");

    expect(back).toEqual(state);
  });

  it("does not hand one board's round to another", () => {
    saveLive("board-a", newRound(5, true));
    expect(loadLive("board-b")).toBeNull();
  });

  it("forgets the round when it is cleared", () => {
    saveLive("board-a", newRound(5, true));
    saveLive("board-a", null);
    expect(loadLive("board-a")).toBeNull();
  });

  it("returns null rather than throwing on a corrupt entry", () => {
    store.setItem("qtr.live.v1", "{not json");
    expect(loadLive("board-a")).toBeNull();
  });

  it("rejects a stored shape that is not a round", () => {
    store.setItem(
      "qtr.live.v1",
      JSON.stringify({ boardId: "board-a", state: { ourPool: "all" }, savedAt: 1 }),
    );
    expect(loadLive("board-a")).toBeNull();
  });

  it("rejects a round whose committed pairings are malformed", () => {
    const bad = { ...newRound(5, true), committed: [{ ours: 0 }] };
    store.setItem(
      "qtr.live.v1",
      JSON.stringify({ boardId: "board-a", state: bad, savedAt: 1 }),
    );
    expect(loadLive("board-a")).toBeNull();
  });

  it("is not vacuous: a well-formed round of the same shape does load", () => {
    // Guards the tests above. If validation ever rejected everything, they would
    // all still pass and prove nothing.
    const good = { ...newRound(5, true), committed: [{ ours: 0, theirs: 1, value: 2 }] };
    store.setItem(
      "qtr.live.v1",
      JSON.stringify({ boardId: "board-a", state: good, savedAt: 1 }),
    );
    expect(loadLive("board-a")).toEqual(good);
  });
});
