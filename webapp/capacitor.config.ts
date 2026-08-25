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
    // Pinned, not inherited. The scheme decides the WebView's origin, and the
    // origin decides which localStorage bucket the boards live in -- so if this
    // default ever moves the way it did between Capacitor 2 and 3, every board
    // and every round on the phone silently becomes someone else's. CI
    // regenerates `android/` from scratch on every run, so there is no checked
    // in project holding the old value. Stating it here is what makes the
    // stored data survive a Capacitor upgrade.
    androidScheme: "https",
  },
};

export default config;
