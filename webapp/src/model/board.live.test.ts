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
import { beforeEach, describe, expect, it, vi } from "vitest";
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

  it("keeps one board's round when another board starts one", () => {
    // Two opponents in one day is the normal case at an event, not an edge one.
    // Tapping through to a second board to check something must not cost the
    // round you are standing in the middle of on the first.
    const a: LiveState = {
      ...newRound(5, true),
      banked: 7,
      committed: [{ ours: 0, theirs: 3, value: 4 }],
    };
    saveLive("board-a", a);
    saveLive("board-b", newRound(5, false));

    expect(loadLive("board-a")).toEqual(a);
  });

  it("clearing one board's round leaves the other alone", () => {
    const b = { ...newRound(5, false), banked: 3 };
    saveLive("board-a", newRound(5, true));
    saveLive("board-b", b);
    saveLive("board-a", null);

    expect(loadLive("board-a")).toBeNull();
    expect(loadLive("board-b")).toEqual(b);
  });

  it("forgets the round when it is cleared", () => {
    saveLive("board-a", newRound(5, true));
    saveLive("board-a", null);
    expect(loadLive("board-a")).toBeNull();
  });

  it("returns null rather than throwing on a corrupt entry", () => {
    store.setItem("qtr.live.v2", "{not json");
    expect(loadLive("board-a")).toBeNull();
  });

  it("rejects a stored shape that is not a round", () => {
    store.setItem(
      "qtr.live.v2",
      JSON.stringify({ "board-a": { boardId: "board-a", state: { ourPool: "all" }, savedAt: 1 } }),
    );
    expect(loadLive("board-a")).toBeNull();
  });

  it("rejects a round whose committed pairings are malformed", () => {
    const bad = { ...newRound(5, true), committed: [{ ours: 0 }] };
    store.setItem(
      "qtr.live.v2",
      JSON.stringify({ "board-a": { boardId: "board-a", state: bad, savedAt: 1 } }),
    );
    expect(loadLive("board-a")).toBeNull();
  });

  it("is not vacuous: a well-formed round of the same shape does load", () => {
    // Guards the tests above. If validation ever rejected everything, they would
    // all still pass and prove nothing.
    const good = { ...newRound(5, true), committed: [{ ours: 0, theirs: 1, value: 2 }] };
    store.setItem(
      "qtr.live.v2",
      JSON.stringify({ "board-a": { boardId: "board-a", state: good, savedAt: 1 } }),
    );
    expect(loadLive("board-a")).toEqual(good);
  });

  it("rescues a round left in the single-slot layout this replaced", () => {
    // Updating mid-event is exactly when someone has a round in the old format,
    // and exactly when losing it would hurt most.
    const state = { ...newRound(5, true), banked: 5 };
    store.setItem(
      "qtr.live.v1",
      JSON.stringify({ boardId: "board-a", state, savedAt: 1 }),
    );

    expect(loadLive("board-a")).toEqual(state);
    expect(loadLive("board-b")).toBeNull();
  });

  it("drops the old slot only once the new layout holds the round", () => {
    const state = { ...newRound(5, true), banked: 5 };
    store.setItem("qtr.live.v1", JSON.stringify({ boardId: "board-a", state, savedAt: 1 }));

    saveLive("board-b", newRound(5, false));

    expect(store.getItem("qtr.live.v1")).toBeNull();
    expect(loadLive("board-a")).toEqual(state);
  });

  it("does not grow without bound", () => {
    // Time is frozen so every save shares a timestamp. That is the hard case:
    // ordering by age alone cannot tell these apart, and picking wrong evicts
    // the round actually being played.
    const now = Date.now();
    const spy = vi.spyOn(Date, "now").mockReturnValue(now);
    try {
      for (let i = 0; i < 20; i++) saveLive(`board-${i}`, { ...newRound(5, true), banked: i });
    } finally {
      spy.mockRestore();
    }

    const kept = Object.keys(JSON.parse(store.getItem("qtr.live.v2")!));
    expect(kept.length).toBeLessThanOrEqual(12);
    // The most recent round is the one being played, so it is the one to keep.
    expect(loadLive("board-19")).not.toBeNull();
  });
});
