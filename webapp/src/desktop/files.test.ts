import { describe, it, expect } from "vitest";

import { createDesktopFiles } from "./files";
import { getDesktopFiles, setDesktopFiles, type DesktopFiles } from "./platform";

describe("createDesktopFiles", () => {
  it("forwards saveBackup to the save_backup command with the contents and default name", async () => {
    const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
    const files = createDesktopFiles(async (cmd, args) => {
      calls.push({ cmd, args });
      return "/tmp/klikklak.json" as never;
    });

    const path = await files.saveBackup('{"a":1}', "klikklak-2025.json");

    expect(path).toBe("/tmp/klikklak.json");
    expect(calls).toEqual([
      {
        cmd: "save_backup",
        args: { contents: '{"a":1}', defaultName: "klikklak-2025.json" },
      },
    ]);
  });

  it("returns null when the save dialog is cancelled", async () => {
    const files = createDesktopFiles(async () => null as never);
    expect(await files.saveBackup("x", "y.json")).toBeNull();
  });

  it("forwards openBackup to the open_backup command and returns its text", async () => {
    const calls: string[] = [];
    const files = createDesktopFiles(async (cmd) => {
      calls.push(cmd);
      return "restored-text" as never;
    });

    expect(await files.openBackup()).toBe("restored-text");
    expect(calls).toEqual(["open_backup"]);
  });
});

describe("desktop files seam", () => {
  it("is null until installed and reads back exactly what was set", () => {
    setDesktopFiles(null);
    expect(getDesktopFiles()).toBeNull();

    const bridge: DesktopFiles = {
      saveBackup: async () => null,
      openBackup: async () => null,
    };
    setDesktopFiles(bridge);
    expect(getDesktopFiles()).toBe(bridge);

    setDesktopFiles(null);
  });
});
