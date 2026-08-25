// @vitest-environment jsdom
/**
 * The splash, checked for the one property that matters.
 *
 * This app gets opened at a table with a round clock running. A launch screen
 * is a nicety; a launch screen that can hold someone is a defect, and the ways
 * it could hold someone are all invisible in a design review:
 *
 *   - the timer never fires, so nothing dismisses it
 *   - the image 404s and the component waits on a load event that never comes
 *   - a tap and the timer race and `onDone` runs twice, so the app advances a
 *     screen too far
 *
 * Every test below is aimed at one of those. The wording, the layout and the
 * art are all placeholders and none of them are asserted on.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Splash } from "./Splash";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

/**
 * Advance the clock the way React wants it advanced.
 *
 * The fade is driven by a `setState` inside a `setTimeout`, which React 19
 * will not have flushed to the DOM by the time the raw timer call returns.
 */
function tick(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

/**
 * jsdom has no `matchMedia`. Splash guards with a `typeof` check and treats a
 * missing implementation as "motion is fine", which is the branch under test
 * everywhere except the reduced-motion case below.
 */
function stubMotion(reduced: boolean) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: reduced,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  );
}

describe("Splash", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("retires itself with no input at all", () => {
    const onDone = vi.fn();
    render(<Splash onDone={onDone} />);

    expect(screen.getByTestId("splash")).toBeTruthy();
    expect(onDone).not.toHaveBeenCalled();

    // The hold, then the fade. Both have to elapse before the app may advance.
    tick(1500);
    expect(onDone).not.toHaveBeenCalled();
    expect(screen.getByTestId("splash").className).toContain("leaving");

    tick(320);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  /*
    The load-failure case. The component never listens for `load` or `error`,
    so this is really a test that it stays that way: if someone later gates the
    dismissal on the image being ready, this fails and says why.
  */
  it("retires itself even when the artwork fails to load", () => {
    const onDone = vi.fn();
    const { container } = render(<Splash onDone={onDone} />);

    const img = container.querySelector("img");
    expect(img).toBeTruthy();
    fireEvent.error(img!);

    tick(1500 + 320);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("gives way to a key press", () => {
    const onDone = vi.fn();
    render(<Splash onDone={onDone} />);

    fireEvent.keyDown(window, { key: "a" });
    tick(320);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("gives way to a tap anywhere", () => {
    const onDone = vi.fn();
    render(<Splash onDone={onDone} />);

    // Anywhere: the listener is on the window, not on the skip hint.
    fireEvent.pointerDown(document.body);
    tick(320);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  /*
    A tap landing near the end of the hold is the likeliest real race, and a
    double call would push the app one screen past the menu.
  */
  it("advances the app once when a tap and the timer collide", () => {
    const onDone = vi.fn();
    render(<Splash onDone={onDone} />);

    tick(1499);
    fireEvent.pointerDown(document.body);
    fireEvent.keyDown(window, { key: "Enter" });
    tick(5000);

    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("drops the animation and shortens the hold under reduced motion", () => {
    stubMotion(true);
    const onDone = vi.fn();
    render(<Splash onDone={onDone} />);

    const el = screen.getByTestId("splash");
    expect(el.className).toContain("still");

    // No fade to wait out: the hold is the whole of it.
    tick(400);
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("splash").className).not.toContain("leaving");
  });

  it("stops its timer when unmounted mid-hold", () => {
    const onDone = vi.fn();
    const { unmount } = render(<Splash onDone={onDone} />);

    unmount();
    tick(5000);
    expect(onDone).not.toHaveBeenCalled();
  });
});
