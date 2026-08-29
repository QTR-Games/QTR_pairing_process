/**
 * Prove, before a release build starts, that the updater signing key in CI is
 * the private half of the public key shipped inside the app.
 *
 * This is the one failure in the whole desktop release path that is invisible.
 * A *missing* key is caught by the bundler; a *mismatched* key is not. The build
 * succeeds, the release publishes, `latest.json` resolves -- and then every
 * installed app rejects the signature and silently keeps running the version it
 * already has. Nothing errors anywhere a human would look. So check it here,
 * cheaply, before the long Rust build: sign a scratch file with the key from the
 * secret and compare the key ID that signature carries against the one in
 * `tauri.conf.json`.
 *
 * Both halves are minisign material. The values Tauri handles -- the `pubkey` in
 * the config, the private key in the secret, the `.sig` the bundler emits -- are
 * all base64 wrappers around plain minisign text whose second line is itself
 * base64 of `algorithm (2 bytes) || key ID (8 bytes) || payload`. That 8-byte key
 * ID identifies the keypair, and it is the only part this needs.
 *
 * Usage: `node scripts/verify-updater-key.mjs` from `webapp/`, with
 * `TAURI_SIGNING_PRIVATE_KEY` (and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, if the
 * key has one) in the environment.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const DOCS = "docs/desktop-release.md";
const CONFIG = join(import.meta.dirname, "../src-tauri/tauri.conf.json");
// The CLI's own JS entry rather than `npx`: Node cannot spawn the `npx.cmd`
// shim without a shell, and this workflow runs on Windows.
const CLI = join(import.meta.dirname, "../node_modules/@tauri-apps/cli/tauri.js");

/**
 * The key ID of a base64-wrapped minisign public key or signature.
 *
 * Rendered the way minisign writes it in its own untrusted comment -- bytes
 * reversed, uppercase hex -- so a mismatch message can be matched by eye against
 * `klikklak-updater.key.pub`.
 */
export function keyIdOf(wrapped) {
  const text = Buffer.from(wrapped.trim(), "base64").toString("utf8");
  const payload = text.split("\n")[1]?.trim();
  if (!payload) throw new Error("not minisign material: no payload line");
  const bytes = Buffer.from(payload, "base64");
  if (bytes.length < 10) throw new Error("not minisign material: payload too short");
  return Buffer.from(bytes.subarray(2, 10)).reverse().toString("hex").toUpperCase();
}

function fail(message) {
  console.error(`::error::${message}`);
  process.exit(1);
}

function main() {
  if (!process.env.TAURI_SIGNING_PRIVATE_KEY) {
    fail(
      `Missing TAURI_SIGNING_PRIVATE_KEY. Publish it with scripts/Publish-UpdaterSecrets.ps1; see ${DOCS}.`,
    );
  }

  const pubkey = JSON.parse(readFileSync(CONFIG, "utf8")).plugins?.updater?.pubkey;
  if (!pubkey) {
    fail(`No plugins.updater.pubkey in ${CONFIG}. See ${DOCS}.`);
  }

  const dir = mkdtempSync(join(tmpdir(), "updater-key-"));
  const probe = join(dir, "probe.txt");
  try {
    writeFileSync(probe, "klikklak updater key check\n");
    // The CLI reads the key and its password straight from the environment, so
    // neither ever reaches a command line or a log.
    try {
      execFileSync(process.execPath, [CLI, "signer", "sign", probe], {
        stdio: ["ignore", "ignore", "inherit"],
      });
    } catch {
      fail(
        `Could not sign with TAURI_SIGNING_PRIVATE_KEY. A wrong TAURI_SIGNING_PRIVATE_KEY_PASSWORD is the usual cause; see ${DOCS}.`,
      );
    }

    const signed = keyIdOf(readFileSync(`${probe}.sig`, "utf8"));
    const shipped = keyIdOf(pubkey);
    if (signed !== shipped) {
      fail(
        `Updater key mismatch: TAURI_SIGNING_PRIVATE_KEY is key ${signed}, but this build ships public key ${shipped}. ` +
          `Every installed app would reject an update from this release. Regenerate both halves together with ` +
          `scripts/New-UpdaterKey.ps1, or point the secret at the matching key; see ${DOCS}.`,
      );
    }
    console.log(`Updater signing key ${signed} matches the public key in the build.`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// Importable by the test, executable in CI.
if (process.argv[1] === import.meta.filename) main();
