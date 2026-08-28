# Cutting a desktop release

The desktop app is the same React bundle that runs in a browser, wrapped by
Tauri and packaged as a Windows installer. There is no separate native build of
the app logic -- that is deliberate, and it is what keeps the phone, the laptop
and the browser showing the same numbers.

You do not need any of this to get an installer. **CI builds one on every push
and pull request** touching `webapp/`, downloadable from the Actions tab as the
`klik-klak-setup` artifact of the `desktop` workflow. That installer is unsigned
and does not auto-update -- it is for a quick look. This document is about the
other path: cutting an actual release that testers can install once and then
have update itself in place.

## The two workflows, and which one you want

| | `desktop.yml` | `release-desktop.yml` |
|---|---|---|
| Runs | every push and pull request under `webapp/` | manual dispatch, or a `desktop-v*` tag |
| Output | an unsigned `-setup.exe` artifact | a **draft GitHub release**: signed installer + `latest.json` |
| Updater | none | signed updater artifacts the app reads on launch |
| Good for | a quick look, and blocking a merge that breaks the desktop build | a laptop you rely on at an event |

Use the release build for anything that matters. The updater only trusts an
installer whose signature matches the public key baked into the app, and only
`release-desktop.yml` produces that signature.

The `desktop-v*` tag prefix is deliberately distinct from the phone app's `v*`
tags (`release-apk.yml`), so the two release pipelines never fire on the same
tag.

## How the auto-update works

Every desktop build carries a minisign **public** key in `tauri.conf.json` under
`plugins.updater.pubkey`, and an endpoint URL:

```
https://github.com/QTR-Games/QTR_pairing_process/releases/latest/download/latest.json
```

On launch -- after the first paint, never before it -- the app fetches that
`latest.json`, compares its version against the running build, and if it is
newer downloads the installer named there and verifies it against the bundled
public key. A signature that does not match is rejected. On Windows the
installer then runs in `passive` mode, replacing the app in place; the user sees
a brief installer flash and the app relaunches on the new version. All of this
is best-effort and silent: offline, no release published yet, or a signature
mismatch simply means the app keeps running the version it already has. The
logic lives in `initDesktopUpdates()` in `webapp/src/desktop/bootstrap.ts`.

`/releases/latest/download/latest.json` resolves to the newest **published,
non-prerelease** release. That is the hinge the whole mechanism turns on, and it
is why the release workflow publishes a *draft*: nothing goes live until a human
publishes it. See [Making a release go live](#making-a-release-go-live).

## Updater signing key: one-time setup

The updater key is a minisign keypair, separate from any Windows code-signing
certificate. The **private** key signs the installer in CI; the **public** key
is committed in `tauri.conf.json` and ships inside every build. Losing the
private key is not fatal the way the Android keystore is -- you can generate a
new pair and ship it in the next build -- but every already-installed copy stops
accepting updates until it is manually reinstalled onto the new key, so treat it
as durable material and back it up.

Generate a pair with the Tauri CLI (this needs only Node, not Rust):

```powershell
cd webapp
npx tauri signer generate -w klikklak-updater.key
```

It writes `klikklak-updater.key` (private) and `klikklak-updater.key.pub`
(public), and prompts for a password. **Keep both files and the password out of
the repository** -- write them somewhere durable and private.

Then set the public key and the two secrets:

1. Copy the entire contents of `klikklak-updater.key.pub` into
   `plugins.updater.pubkey` in `webapp/src-tauri/tauri.conf.json`. It is the raw
   key text, not a path.
2. Set two repository secrets (Settings -> Secrets and variables -> Actions):
   - `TAURI_SIGNING_PRIVATE_KEY` -- the entire contents of the private
     `klikklak-updater.key` file.
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` -- the password you chose.

The exact secret names matter. Tauri v2 reads `TAURI_SIGNING_PRIVATE_KEY` and
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`; the v1 names (`TAURI_PRIVATE_KEY`,
`TAURI_KEY_PASSWORD`) are silently ignored and produce an *unsigned* artifact
that no installed app will accept. `release-desktop.yml` fails loudly before
building if `TAURI_SIGNING_PRIVATE_KEY` is missing, precisely because that
failure is otherwise invisible until an update silently never arrives.

## Cutting a release

Manual dispatch is the normal path. From the Actions tab, run **Release
Desktop** and give it a version with no leading `v` (e.g. `2.2.0`). The workflow
stamps that version into `tauri.conf.json`, builds and signs, and creates the
tag `desktop-v2.2.0` along with a draft release.

Alternatively, push a tag you have already cut:

```powershell
git tag desktop-v2.2.0
git push origin desktop-v2.2.0
```

The version is taken from the tag name with the `desktop-v` prefix stripped.
Either way the release is created as a **draft**.

## Making a release go live

The build finishing does **not** ship anything to anyone. The release is a
draft, and `/releases/latest/download/latest.json` ignores drafts, so installed
apps see nothing until you publish.

1. Open the draft release under the repository's Releases.
2. Download the `-setup.exe` and install it on a clean machine. Confirm the app
   launches and shows the new version.
3. When you are satisfied, click **Publish release**.

Only at that point does `latest.json` resolve for the fleet, and installed apps
pick up the update on their next launch. To pull a bad release, unpublish it
back to a draft (or delete it) and the previous published release becomes
`latest` again.

The first ever release is the exception that has no auto-update path in: there
is nothing installed yet to update *from*. Hand testers the `-setup.exe` from
that first published release directly. Every release after that one updates in
place.

## Optional: Windows Authenticode signing

The updater signature proves an installer came from this pipeline. It does
nothing about the SmartScreen warning Windows shows for an installer from an
unknown publisher -- that requires an Authenticode certificate, which is a
separate, paid, identity-verified certificate you obtain yourself.

This is wired but off by default. Set a repository secret
`WINDOWS_CERTIFICATE_THUMBPRINT` to the thumbprint of a certificate installed in
the runner's certificate store, and `release-desktop.yml` injects it through an
out-of-tree `--config` file at build time. It is kept out of `tauri.conf.json`
on purpose: a machine-specific thumbprint there would break the unsigned
`desktop.yml` PR gate, and only the release path has a certificate anyway. With
no secret set, the release installer is updater-signed but not
Authenticode-signed, and behaves exactly like the PR-gate build.

Azure Trusted Signing is the modern alternative to holding a certificate
yourself; it is configured through `bundle.windows.signCommand` rather than a
thumbprint. It is out of scope here -- wire it into the same optional
`--config` step if you adopt it.

## Retiring the old Tkinter desktop

The Python/Tkinter desktop under the repository root (`main.py`, `entrypoint.py`,
`ui_manager*.py` and friends) is the previous desktop app. It is superseded by
this Tauri build, but retiring it is a separate, deliberate change with its own
guardrails -- it is not part of setting up releases. Do not delete it as a side
effect of a release. Track that work on its own.

## Troubleshooting

**The `desktop` PR check builds fine but the release fails at signing.** The two
secrets are the usual cause. `release-desktop.yml` checks for
`TAURI_SIGNING_PRIVATE_KEY` up front, but a wrong *password* surfaces later as a
signer error mid-build. Confirm `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` matches the
password you set when generating the key.

**A release published but installed apps are not updating.** Three things to
check, in order: the release is *published*, not still a draft; it is not marked
as a pre-release (pre-releases are excluded from `latest`); and the running app
was built *after* the public key in `tauri.conf.json` was set -- a build carrying
no key, or an older key, cannot verify the new signature. The version in
`latest.json` must also be strictly higher than the installed one.

**Updates verify-fail silently.** The installer was signed with a private key
that does not match the `pubkey` shipped in the app. This happens if the key was
regenerated but `tauri.conf.json` was not updated, or vice versa. The public key
in the build and the private key in `TAURI_SIGNING_PRIVATE_KEY` must be halves of
the same pair. Regenerate both together if in doubt.

**SmartScreen warns about an unknown publisher.** Expected without Authenticode
signing -- the updater signature does not affect it. See
[Optional: Windows Authenticode signing](#optional-windows-authenticode-signing).
