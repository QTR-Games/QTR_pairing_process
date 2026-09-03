// @vitest-environment jsdom
/**
 * Android back/gesture during a round (issue #132). The contract that matters
 * is the fall-through: a press only undoes when there is something to undo,
 * so a captain at the start of a round still gets the platform's own back
 * rather than a button that silently eats the gesture.
 */
import { cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useBackGesture } from "./useBackGesture";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

/** Fire the event Capacitor's Android shell produces for the back button. */
function pressBack() {
  window.dispatchEvent(new PopStateEvent("popstate"));
}

describe("useBackGesture", () => {
  it("undoes a step when there is one, and stays in the round", () => {
    const onBack = vi.fn();
    renderHook(() => useBackGesture(true, true, onBack));

    pressBack();

    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("keeps catching presses, not just the first", () => {
    const onBack = vi.fn();
    renderHook(() => useBackGesture(true, true, onBack));

    pressBack();
    pressBack();
    pressBack();

    expect(onBack).toHaveBeenCalledTimes(3);
  });

  it("lets the press through when there is nothing to undo", () => {
    const onBack = vi.fn();
    renderHook(() => useBackGesture(true, false, onBack));

    pressBack();

    expect(onBack).not.toHaveBeenCalled();
  });

  it("does nothing at all outside a round", () => {
    const onBack = vi.fn();
    renderHook(() => useBackGesture(false, true, onBack));

    pressBack();

    expect(onBack).not.toHaveBeenCalled();
  });

  it("picks up a canUndo that flips after mount", () => {
    const onBack = vi.fn();
    const { rerender } = renderHook(
      ({ can }) => useBackGesture(true, can, onBack),
      { initialProps: { can: false } },
    );

    pressBack();
    expect(onBack).not.toHaveBeenCalled();

    rerender({ can: true });
    pressBack();
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("stops listening once the round is left", () => {
    const onBack = vi.fn();
    const { unmount } = renderHook(() => useBackGesture(true, true, onBack));

    unmount();
    pressBack();

    expect(onBack).not.toHaveBeenCalled();
  });
});
