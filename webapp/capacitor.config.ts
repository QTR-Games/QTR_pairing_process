import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Native shell configuration.
 *
 * The web build already sets `base: './'`, so the same `dist` that ships to
 * GitHub Pages loads unmodified inside the WebView, which Capacitor serves from
 * a local `https://localhost` origin rather than over the network. Nothing is
 * fetched at runtime, so the app works in a hall with no signal.
 * There is no separate native build of the app -- the APK is a wrapper around
 * the identical bundle, which is what keeps the phone and the laptop showing
 * the same numbers.
 *
 * The `android/` project IS committed, under `webapp/android/`. It has to be:
 * release signing config, versionCode resolution and any native plugin source
 * all live inside the Gradle project, and a regenerated project throws them
 * away every run. The cost is that it is a second thing to keep current -- when
 * Capacitor updates, re-run `npx cap sync android` and review the diff rather
 * than letting it drift. The generated parts (copied web assets,
 * `capacitor.config.json`, `.gradle/`, `build/`) stay ignored by
 * `webapp/android/.gitignore`, so only the parts we author are tracked.
 */
const config: CapacitorConfig = {
  appId: "com.gronksoft.klikklak",
  // The Android package identity, and effectively permanent: changing it
  // orphans every existing install rather than upgrading it, so the app has to
  // be uninstalled first and its saved boards go with it. It was changed from
  // `com.qtrgames.pairing` exactly once, at the same moment the app moved from
  // debug signing to a real release key -- that switch already forced a
  // one-time uninstall, so the rename rode along for free. Do not change it
  // again without a comparably good reason.
  appName: "KLIK KLAK",
  webDir: "dist",
  android: {
    // Round totals are the point of the app; a WebView that reflows text on
    // its own idea of a comfortable size makes columns of numbers disagree
    // with the laptop.
    allowMixedContent: false,
    // Pinned, not inherited. The scheme decides the WebView's origin, and the
    // origin decides which localStorage bucket the boards live in -- so if this
    // default ever moves the way it did between Capacitor 2 and 3, every board
    // and every round on the phone silently becomes someone else's. The
    // committed `android/` project records the current value, but a `cap sync`
    // after a Capacitor upgrade would rewrite it. Stating it here is what makes
    // the stored data survive that upgrade.
    androidScheme: "https",
  },
};

export default config;
