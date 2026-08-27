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

const {
  loadSettings,
  saveSettings,
  DEFAULTS,
  DODGE_MODES,
  ADVICE_LEVELS,
  SURPRISE_MODES,
} =
  await import("./settings");

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

  it("explains in full by default", () => {
    // The newer captain is the one who cannot yet tell a safe silence from a
    // missed trap, so the reasoning is on until a veteran turns it down.
    expect(loadSettings().adviceLevel).toBe("full");
    expect(DEFAULTS.adviceLevel).toBe("full");
  });

  it("remembers every mode across a reload", () => {
    for (const mode of DODGE_MODES) {
      saveSettings({
        dodgeMode: mode.id,
        adviceLevel: DEFAULTS.adviceLevel,
        surpriseMode: DEFAULTS.surpriseMode,
        surpriseRegretThreshold: DEFAULTS.surpriseRegretThreshold,
      });
      expect(loadSettings().dodgeMode).toBe(mode.id);
    }
  });

  it("remembers every advice level across a reload", () => {
    for (const level of ADVICE_LEVELS) {
      saveSettings({
        dodgeMode: DEFAULTS.dodgeMode,
        adviceLevel: level.id,
        surpriseMode: DEFAULTS.surpriseMode,
        surpriseRegretThreshold: DEFAULTS.surpriseRegretThreshold,
      });
      expect(loadSettings().adviceLevel).toBe(level.id);
    }
  });

  it("offers exactly the three states, once each", () => {
    const ids = DODGE_MODES.map((m) => m.id);
    expect(new Set(ids)).toEqual(new Set(["off", "onDemand", "always"]));
    expect(ids).toHaveLength(3);
  });

  it("offers exactly the three advice levels, once each", () => {
    const ids = ADVICE_LEVELS.map((m) => m.id);
    expect(new Set(ids)).toEqual(new Set(["full", "brief", "off"]));
    expect(ids).toHaveLength(3);
  });

  it("keeps surprise detection off by default", () => {
    expect(loadSettings().surpriseMode).toBe("off");
    expect(DEFAULTS.surpriseMode).toBe("off");
    expect(loadSettings().surpriseRegretThreshold).toBe(0);
  });

  it("remembers every surprise mode across a reload", () => {
    for (const mode of SURPRISE_MODES) {
      saveSettings({
        dodgeMode: DEFAULTS.dodgeMode,
        adviceLevel: DEFAULTS.adviceLevel,
        surpriseMode: mode.id,
        surpriseRegretThreshold: DEFAULTS.surpriseRegretThreshold,
      });
      expect(loadSettings().surpriseMode).toBe(mode.id);
    }
  });

  it("remembers a non-negative surprise threshold across a reload", () => {
    saveSettings({
      dodgeMode: DEFAULTS.dodgeMode,
      adviceLevel: DEFAULTS.adviceLevel,
      surpriseMode: DEFAULTS.surpriseMode,
      surpriseRegretThreshold: 1.5,
    });
    expect(loadSettings().surpriseRegretThreshold).toBe(1.5);
  });

  it("falls back to defaults rather than throwing on rubbish", () => {
    for (const junk of [
      "",
      "not json",
      "null",
      "[]",
      "42",
      '{"dodgeMode":"banana"}',
      '{"adviceLevel":"banana"}',
      '{"surpriseMode":"banana"}',
      '{"surpriseRegretThreshold":-1}',
    ]) {
      store.setItem(KEY, junk);
      expect(() => loadSettings()).not.toThrow();
      expect(loadSettings().dodgeMode).toBe(DEFAULTS.dodgeMode);
      expect(loadSettings().adviceLevel).toBe(DEFAULTS.adviceLevel);
      expect(loadSettings().surpriseMode).toBe(DEFAULTS.surpriseMode);
      expect(loadSettings().surpriseRegretThreshold).toBe(DEFAULTS.surpriseRegretThreshold);
    }
  });

  it("keeps a known field when an unknown one sits beside it", () => {
    // A settings file written by a later version should still hand back the
    // parts this version understands.
    store.setItem(KEY, JSON.stringify({ dodgeMode: "always", somethingNew: true }));
    expect(loadSettings().dodgeMode).toBe("always");
    // And a missing sibling field takes its default rather than undefined.
    expect(loadSettings().adviceLevel).toBe(DEFAULTS.adviceLevel);
    expect(loadSettings().surpriseMode).toBe(DEFAULTS.surpriseMode);
  });

  it("keeps each preference independent of the other", () => {
    // The two toggles share one storage key; setting one must not reset the
    // other back to its default on the next read.
    store.setItem(
      KEY,
      JSON.stringify({
        dodgeMode: "always",
        adviceLevel: "off",
        surpriseMode: "on",
        surpriseRegretThreshold: 1,
      }),
    );
    const loaded = loadSettings();
    expect(loaded.dodgeMode).toBe("always");
    expect(loaded.adviceLevel).toBe("off");
    expect(loaded.surpriseMode).toBe("on");
    expect(loaded.surpriseRegretThreshold).toBe(1);
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
      const next = {
        dodgeMode: "off" as const,
        adviceLevel: "brief" as const,
        surpriseMode: "on" as const,
        surpriseRegretThreshold: 0.5,
      };
      expect(() => saveSettings(next)).not.toThrow();
      expect(saveSettings(next).dodgeMode).toBe("off");
      expect(saveSettings(next).adviceLevel).toBe("brief");
      expect(saveSettings(next).surpriseMode).toBe("on");
      expect(saveSettings(next).surpriseRegretThreshold).toBe(0.5);
    } finally {
      (globalThis as unknown as { localStorage: unknown }).localStorage = real;
    }
  });
});
