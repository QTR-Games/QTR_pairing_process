/**
 * Settings survive a reload, and a corrupt file does not cost you a round.
 *
 * The dodge mode is the first app-wide preference in the app, so this also
 * fixes the shape of the storage: field-by-field validation on read, defaults
 * on anything unrecognised, and no throw on any input. An event-day app that
 * crashes on a bad preference is worse than one that quietly ignores it.
 *
 * Vitest runs in the node environment here, so there is no `localStorage`. A
 * small stub is cheaper than adding jsdom to the toolchain for two functions --
 * same approach as board.live.test.ts.
 */
import { describe, expect, it, beforeEach } from "vitest";

class MemoryStorage {
  private data = new Map<string, string>();
  getItem(k: string): string | null {
    return this.data.has(k) ? (this.data.get(k) as string) : null;
  }
  setItem(k: string, v: string): void {
    this.data.set(k, v);
  }
  removeItem(k: string): void {
    this.data.delete(k);
  }
  clear(): void {
    this.data.clear();
  }
}

const store = new MemoryStorage();
(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = store;

const { loadSettings, saveSettings, DEFAULTS, DODGE_MODES } = await import("./settings");

const KEY = "qtr.settings.v1";

describe("app settings", () => {
  beforeEach(() => store.clear());

  it("asks first by default", () => {
    // Not an arbitrary default. The insight has something to say on all 31
    // saved boards, so "always" would mean one more permanent line on every
    // screen, and "off" would mean a feature you own but never see.
    expect(loadSettings().dodgeMode).toBe("onDemand");
    expect(DEFAULTS.dodgeMode).toBe("onDemand");
  });

  it("remembers every mode across a reload", () => {
    for (const mode of DODGE_MODES) {
      saveSettings({ dodgeMode: mode.id });
      expect(loadSettings().dodgeMode).toBe(mode.id);
    }
  });

  it("offers exactly the three states, once each", () => {
    const ids = DODGE_MODES.map((m) => m.id);
    expect(new Set(ids)).toEqual(new Set(["off", "onDemand", "always"]));
    expect(ids).toHaveLength(3);
  });

  it("falls back to defaults rather than throwing on rubbish", () => {
    for (const junk of ["", "not json", "null", "[]", "42", '{"dodgeMode":"banana"}']) {
      store.setItem(KEY, junk);
      expect(() => loadSettings()).not.toThrow();
      expect(loadSettings().dodgeMode).toBe(DEFAULTS.dodgeMode);
    }
  });

  it("keeps a known field when an unknown one sits beside it", () => {
    // A settings file written by a later version should still hand back the
    // parts this version understands.
    store.setItem(KEY, JSON.stringify({ dodgeMode: "always", somethingNew: true }));
    expect(loadSettings().dodgeMode).toBe("always");
  });

  it("still applies the setting when storage refuses to write", () => {
    const broken = {
      getItem: () => null,
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
      removeItem: () => {},
    };
    const real = (globalThis as unknown as { localStorage: unknown }).localStorage;
    (globalThis as unknown as { localStorage: unknown }).localStorage = broken;
    try {
      expect(() => saveSettings({ dodgeMode: "off" })).not.toThrow();
      expect(saveSettings({ dodgeMode: "off" }).dodgeMode).toBe("off");
    } finally {
      (globalThis as unknown as { localStorage: unknown }).localStorage = real;
    }
  });
});
