/**
 * The sticky header keeps clear of the status bar.
 *
 * `index.html` sets `viewport-fit=cover`, which is what lets the dark
 * background reach the notch -- and also what puts the top of the viewport
 * underneath the system clock in a standalone WebView. The header is
 * `position: sticky; top: 0`, so without `env(safe-area-inset-top)` in its
 * padding the Menu button sits behind the clock and cannot be tapped. That was
 * issue #116, and it is invisible on a laptop: every browser and every desktop
 * build reports the inset as `0px`, so the bug only exists on the phone.
 *
 * That invisibility is the reason for a test, and for this shape of test. The
 * fix is one CSS declaration with no runtime behaviour to observe: jsdom does
 * not resolve `env()` (or `calc()`, or the cascade across a media query), so
 * rendering the header and reading its computed padding would assert nothing.
 * Reading the stylesheet is the only check available that would actually have
 * failed before the fix.
 *
 * Both rules are checked. `.app-wide .app-head` uses the `padding` shorthand,
 * so it silently resets the top value the base rule computes -- a wide screen
 * with a real inset, an Android tablet in fullscreen, would regress on its own
 * while the phone stayed correct.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const css = readFileSync(fileURLToPath(new URL("./styles.css", import.meta.url)), "utf8");

/**
 * The declarations of the first rule whose selector matches exactly.
 *
 * Deliberately crude -- a brace-counting reader, not a CSS parser -- because
 * the alternative is a dependency for one assertion. It is enough for these
 * two rules, neither of which nests anything.
 */
function ruleBody(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  expect(start, `no rule found for "${selector}"`).toBeGreaterThanOrEqual(0);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

describe("app header safe-area handling", () => {
  it("pads the phone header past the status bar", () => {
    expect(ruleBody(".app-head")).toMatch(/padding:[^;]*env\(safe-area-inset-top/);
  });

  it("keeps the inset in the wide override, which resets the shorthand", () => {
    expect(ruleBody(".app-wide .app-head")).toMatch(/padding:[^;]*env\(safe-area-inset-top/);
  });

  it("falls back to 0px, so a browser with no inset is unaffected", () => {
    expect(ruleBody(".app-head")).toContain("env(safe-area-inset-top, 0px)");
    expect(ruleBody(".app-wide .app-head")).toContain("env(safe-area-inset-top, 0px)");
  });
});
