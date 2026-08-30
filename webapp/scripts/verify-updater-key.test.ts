import { readFileSync } from "node:fs";
import { describe, it, expect } from "vitest";

import { keyIdOf } from "./verify-updater-key.mjs";

/*
 * Real minisign material from a throwaway keypair: the public key and a
 * signature made with its private half. Both are public artifacts by nature --
 * a released build ships the first and a released installer ships the second --
 * so there is nothing here to keep secret. Generated fixtures rather than
 * hand-built bytes, because the point of the check is that it reads what the
 * Tauri CLI actually writes.
 */
const PUBLIC_KEY =
  "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDlEQjU3RjJDOUY0MjQ4MjAKUldRZ1NFS2ZMSCsxbmJER09yNnBHYmtWbTY4Qk5OUGdSZzhidzd6VUltR0E0bElwaklNNkcrSmUK";
const SIGNATURE =
  "dW50cnVzdGVkIGNvbW1lbnQ6IHNpZ25hdHVyZSBmcm9tIHRhdXJpIHNlY3JldCBrZXkKUlVRZ1NFS2ZMSCsxblMyR01ZTThmb2ZuWEcyMWUxNmtFOXhURWhCdXd1T25xQ09rNDIxRzhuamJ0anllRlk4THFSQkVDNU5Qd0xiejdIZnZyTGtDZFdnK25EWEtuZm03VkFRPQp0cnVzdGVkIGNvbW1lbnQ6IHRpbWVzdGFtcDoxNzg4MDE3NDkxCWZpbGU6cDIudHh0CnhoWnF2MFdlc1R4NXFHQ2JxTDZ3MU1YcVdrVFVMRkc5ZkszSlJMcXdYK2p3czA5K0NBbFMyd2RHS25GNEFNN2F6MHFXQVNvdm1TSk91dUJNenMwVEJ3PT0K";

describe("keyIdOf", () => {
  it("reads the key ID minisign prints in its own comment", () => {
    // The comment inside PUBLIC_KEY reads "minisign public key: 9DB57F2C9F424820".
    expect(keyIdOf(PUBLIC_KEY)).toBe("9DB57F2C9F424820");
  });

  it("reads the same key ID from a signature made with the matching private key", () => {
    expect(keyIdOf(SIGNATURE)).toBe(keyIdOf(PUBLIC_KEY));
  });

  it("separates a signature made by a different key -- the silent release failure", () => {
    const other = JSON.parse(
      readFileSync(new URL("../src-tauri/tauri.conf.json", import.meta.url), "utf8"),
    ).plugins.updater.pubkey;

    expect(keyIdOf(other)).not.toBe(keyIdOf(SIGNATURE));
  });

  it("rejects anything that is not minisign material", () => {
    expect(() => keyIdOf(Buffer.from("not a key").toString("base64"))).toThrow();
    expect(() =>
      keyIdOf(Buffer.from("untrusted comment: x\nc2hvcnQ=\n").toString("base64")),
    ).toThrow();
  });
});

describe("the public key committed in tauri.conf.json", () => {
  it("is well-formed minisign material a build can verify against", () => {
    const pubkey = JSON.parse(
      readFileSync(new URL("../src-tauri/tauri.conf.json", import.meta.url), "utf8"),
    ).plugins.updater.pubkey;

    expect(pubkey).toBeTruthy();
    expect(keyIdOf(pubkey)).toMatch(/^[0-9A-F]{16}$/);
  });
});
