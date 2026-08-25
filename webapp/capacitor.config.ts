import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Native shell configuration.
 *
 * The web build already sets `base: './'`, so the same `dist` that ships to
 * GitHub Pages loads unmodified from the `file://` origin a WebView gives us.
 * There is no separate native build of the app -- the APK is a wrapper around
 * the identical bundle, which is what keeps the phone and the laptop showing
 * the same numbers.
 *
 * The `android/` project is NOT committed. CI regenerates it with `cap add`
 * on every run, because a checked-in Gradle project is a second thing to keep
 * current and it would drift the moment Capacitor updates.
 */
const config: CapacitorConfig = {
  appId: "com.qtrgames.pairing",
  appName: "QTR Pairing",
  webDir: "dist",
  android: {
    // Round totals are the point of the app; a WebView that reflows text on
    // its own idea of a comfortable size makes columns of numbers disagree
    // with the laptop.
    allowMixedContent: false,
  },
};

export default config;
