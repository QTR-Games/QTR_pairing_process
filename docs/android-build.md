# Building the Android app

The phone app is the same React bundle that runs in a browser, wrapped by
Capacitor and packaged as an APK. There is no separate native build of the app
logic -- that is deliberate, and it is what keeps the phone and the laptop
showing the same numbers.

You do not need any of this to get an APK. **CI builds one on every push to
`main` and on every pull request**, downloadable from the Actions tab as the
`klikklak-apk` artifact. This document is for building locally, and for
setting up release signing.

## The two workflows, and which one you want

| | `build-phone-app.yml` | `release-apk.yml` |
|---|---|---|
| Runs | every push to `main`, every pull request, or manual dispatch | manual dispatch, or a `v*` tag |
| Build type | `assembleDebug` | `assembleRelease` |
| Signed with | throwaway debug key | the project's own release key |
| Good for | a quick look, and blocking a merge that breaks the phone build | a phone you rely on at an event |

Use the release APK for anything that matters. A debug APK is signed with a key
generated on the runner, which is different on every build, so Android treats
each one as a different app and refuses to upgrade in place.

## Prerequisites for a local build

### JDK 21, and it must be Temurin

Two separate traps here, both of which cost real time if you hit them blind.

**It must be 21.** Capacitor 8 pins `VERSION_21` in
`node_modules/@capacitor/android/capacitor/build.gradle`. JDK 17 gets as far as
`:capacitor-android:compileDebugJavaWithJavac` and then fails with
`error: invalid source release: 21`.

**It must be Temurin.** Oracle JDK 21.0.9 does not fail -- it *hangs*, forever,
at `:app:mergeProjectDexDebug`. Roughly six cores peg, the heap stays flat (so
it is not garbage collection or an `-Xmx` problem), and the JVM never reaches a
safepoint, so `jcmd Thread.print` attaches and hangs without producing a dump.
It reads exactly like a slow build. It will never finish. Temurin
`21.0.12.1+1` builds the identical tree in about 76 seconds.

Changing Android SDK build-tools cannot help: D8 and R8 ship inside the Android
Gradle Plugin as `com.android.tools:r8`, not in build-tools.

```powershell
winget install EclipseAdoptium.Temurin.21.JDK
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.7-hotspot'
```

If you have several JDKs installed and do not want to change `JAVA_HOME`, point
Gradle at one for a single build. **Quote it** -- an unquoted value truncates at
the first space in `Program Files`:

```powershell
.\gradlew.bat "-Dorg.gradle.java.home=C:\Program Files\Eclipse Adoptium\jdk-21.0.12.7-hotspot" assembleDebug
```

### Node 22 or newer

Capacitor 8's CLI refuses to run below 22.

### Android SDK

Android Studio installs it, or use the command-line tools. The build needs
platform `android-36` and build-tools `36.0.0`. Gradle finds the SDK through
`ANDROID_HOME`, or through `webapp/android/local.properties` (gitignored --
create it yourself if you need it).

## Building

```powershell
cd webapp
npm ci
npm run android:build:debug
```

The APK lands at
`webapp/android/app/build/outputs/apk/debug/app-debug.apk`.

`android:build:debug` runs `npm run build` (Vite) and then `cap sync android`
before Gradle. That ordering matters: `cap sync` copies `dist/` into the native
project, so the web bundle has to be current before the APK is assembled.

To install straight onto a connected device with USB debugging on:

```powershell
cd webapp
npm run android:install
```

## What is committed, and what is not

`webapp/android/` **is** committed. It has to be -- release signing config,
versionCode resolution and any native plugin source all live inside the Gradle
project, and regenerating it with `cap add` on every build throws them away.

The generated parts stay ignored by `webapp/android/.gitignore`:

- `app/src/main/assets/public/` -- the copied web bundle
- `app/src/main/assets/capacitor.config.json`
- `capacitor-cordova-android-plugins/`
- `.gradle/`, `build/`, `local.properties`

Because those are absent from a fresh checkout, **`cap sync` must run before
Gradle**. `settings.gradle` references `:capacitor-cordova-android-plugins`, so
Gradle fails at configuration time if that directory does not exist yet. Both
workflows create the directories and run `cap sync` before touching Gradle;
`npm run android:sync` does the same locally.

After a Capacitor upgrade, run `npx cap sync android` and **review the diff**
rather than accepting it blindly. That is the cost of committing the project.
Pay particular attention to `androidScheme` -- see `webapp/capacitor.config.ts`
for why it is pinned.

## versionCode: the reason an install fails silently

Android refuses to install an APK whose `versionCode` is lower than or equal to
the one already on the device, and the failure surfaces as a terse *"App not
installed"* with no explanation.

The stock Capacitor template hardcodes `versionCode 1` for every build, so the
second APK you ever sideload is rejected. `webapp/android/app/build.gradle`
resolves it instead, in this order:

1. `ANDROID_VERSION_CODE` environment variable -- what CI sets
2. `qtrVersionCode` in `webapp/android/gradle.properties` -- the local fallback
3. `1`

CI uses the workflow run number, which is monotonic per repository and so never
regresses. If you sideload two *local* builds in a row onto the same device,
bump `qtrVersionCode` in `gradle.properties` by hand between them.

## Release signing

The keystore is the permanent identity of the app. Android only installs an
update over an existing install when both are signed by the same key, so losing
it means every phone running the app has to uninstall before it can take another
build. Back up the `.jks` and its password somewhere durable.

Nothing here is ever committed: `*.jks` and `webapp/android/keystore.properties`
are both gitignored.

### One-time setup

```powershell
cd webapp
npm run android:keystore:create   # creates the keystore + keystore.properties
npm run android:signing:secrets   # uploads them as repository secrets
```

The first command writes `webapp/android/app/qtr-release.jks` and a gitignored
`webapp/android/keystore.properties` holding a generated 32-character password.
The second reads both and sets four repository secrets over stdin, so no secret
ever appears on a command line:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

### Producing a signed build

Run the **Release APK** workflow from the Actions tab, supplying a version name
and a version code higher than the last one you installed. The workflow verifies
all four secrets are present *before* building, decodes the keystore outside the
workspace, assembles, and then runs `apksigner verify --print-certs` as proof
rather than assumption. The decoded keystore is deleted in an `always()` step.

`build.gradle` only *warns* when signing material is absent rather than failing,
so PR CI and a fresh clone can still assemble an unsigned APK. The workflow is
where the hard check lives.

## Installing on a phone over Wi-Fi

`scripts/Install-ToPhone.ps1` puts the latest CI build on a phone in one
command, with no cable and without moving the APK through cloud storage:

```powershell
cd webapp
npm run phone:install
```

It finds the most recent successful **Release APK** run, downloads the artifact,
installs it over wireless debugging, and launches the app. The download is
cached per run id, so reinstalling the same build costs nothing while a new
build is picked up automatically.

### What it needs installed

Two tools, both looked up in the usual install locations as well as on `PATH`:

- **adb**, from the Android SDK platform-tools (see [Android SDK](#android-sdk)).
- **the GitHub CLI (`gh`)**, which is what downloads the CI artifact:

  ```powershell
  winget install --id GitHub.cli
  gh auth login
  ```

  Open a new terminal afterwards -- a PATH change does not reach terminals that
  were already running. Note that a `gh` bundled inside some other application
  does not count: those are on the PATH of that application's own child
  processes only, so the command can appear to work in one window and be missing
  in another. `gh --version` in the terminal you actually use is the check that
  matters.

Neither tool is needed for `-ApkPath`, and only adb is needed for `-Local`.

### One-time pairing

On the phone, enable *Developer options -> Wireless debugging*. That screen
shows a `host:port`, and tapping **Pair device with pairing code** shows a
*different* `host:port` plus a six-digit code. Both are needed the first time:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Install-ToPhone.ps1 `
  -PairAddress 192.168.1.50:37021 -PairCode 123456 -Device 192.168.1.50:41234
```

The two ports being different is the single most common cause of a failed pair.
The pairing port is one-time and the code expires within a few minutes.

The connect address is then remembered in
`%LOCALAPPDATA%\KlikKlak\phone-device.json` -- machine-local configuration
rather than project configuration, since another laptop pairs with a different
phone on a different network -- and later runs need no arguments.

Android issues a **new port** every time wireless debugging is toggled off and
on, and after most reboots. Pairing survives that; the port does not. When a
remembered address stops connecting, pass the current one with `-Device`.

### Other sources

| Flag | Installs |
| --- | --- |
| *(none)* | Latest successful CI **Release APK** run |
| `-Local` | A release build from the working tree |
| `-Local -DebugVariant` | A debug build from the working tree |
| `-ApkPath <file>` | A specific APK |
| `-Usb` | Same, over a cable instead of Wi-Fi |

`-DebugVariant` is off by default on purpose. A debug APK is signed with a
throwaway key, so Android refuses to install it over the release build already
on the phone and reports a signature mismatch that says nothing about the cause.
The script detects that case and explains it.

`adb` does not need to be on PATH. It is discovered from `ANDROID_HOME`,
`ANDROID_SDK_ROOT`, then `%LOCALAPPDATA%\Android\Sdk`, because a stock Android
Studio install sets none of them.

## Before an event

Install on every phone that needs it **ahead of time**, from a laptop, with
`npm run phone:install`. Once installed the app is entirely offline: it bundles
its own web assets, sets no `server.url`, makes no network request at runtime,
and keeps boards in `localStorage` on the device. Venue wifi cannot affect it,
and neither can the venue not having any.

There is deliberately no URL-based fallback any more. There used to be one -- a
manual GitHub Pages deploy that served the bundle and the APK from a public
Pages URL on the day. It is gone and should not be re-added. This
repository is private and the organisation is on the GitHub Free plan, where
Pages cannot publish from a private repository at all, so the fallback would
have failed at exactly the moment it was needed. Restoring it would mean paying
for a plan *and* accepting that Pages sites are public regardless of repository
visibility, which would put the team's rosters and ratings on a guessable URL.
Installing ahead of time costs one command per phone and has none of that.

## Troubleshooting

**`:app:validateSigningDebug` fails.** The debug keystore is missing; it is not
always auto-created. Recreate it with the fixed AOSP values -- do not substitute
your own, or Android Studio and Gradle will disagree about the debug identity:

```powershell
keytool -genkeypair -v -keystore "$env:USERPROFILE\.android\debug.keystore" `
  -storepass android -keypass android -alias androiddebugkey `
  -keyalg RSA -keysize 2048 -validity 10000 `
  -dname "CN=Android Debug, O=Android, C=US"
```

**Gradle fails at configuration with a missing
`capacitor-cordova-android-plugins` project.** You ran Gradle before `cap sync`.
Run `npm run android:sync` first.

**The build hangs at `:app:mergeProjectDexDebug`.** You are on Oracle JDK.
See above -- it will not finish.

**Maven Central returns 429 or 403.** It has broken this build twice for reasons
unrelated to the code. Both workflows retry five times with a doubling backoff
(30s, 60s, 120s, 240s), which rides out roughly eight minutes. Locally, just
run it again.

**"App not installed" on the phone.** Almost always versionCode -- see above.
Failing that, check that the phone allows installing from unknown sources for
whichever app is opening the APK (usually the file manager or browser). This
does not apply to `Install-ToPhone.ps1`, which installs through adb and so never
goes through the unknown-sources prompt at all.

**"The GitHub CLI (gh) was not found."** `Install-ToPhone.ps1` uses `gh` to
download the CI artifact, and it is not installed by default. See
[What it needs installed](#what-it-needs-installed). The trap worth knowing: a
`gh` that ships inside another application is only on the PATH of that
application's own child processes, so the same script can work when launched one
way and fail when launched from an ordinary terminal. Run `gh --version` in the
terminal you are actually using. To install the app without `gh` at all, pass
`-ApkPath` with an APK you already have.

**`adb pair` fails with "failed to authenticate".** The `-PairAddress` port is
almost certainly the one from the main wireless debugging screen rather than the
one in the pairing dialog. They are different, and only the dialog's port pairs.
The code also expires within a few minutes.

**A previously working `-Device` address stops connecting.** Android issues a new
port whenever wireless debugging is toggled or the phone reboots. Read the
current `host:port` off the phone and pass it once with `-Device`; the pairing
itself is still intact.

**`adb devices` shows the phone as `unauthorized`.** The "Allow debugging?"
prompt on the phone was dismissed or has not been answered yet. Accept it and
rerun.
