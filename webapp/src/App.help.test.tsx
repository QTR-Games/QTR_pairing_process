// @vitest-environment jsdom
/**
 * Where the contextual help "?" appears, and where it deliberately does not.
 *
 * HelpOverlay.test.tsx covers the mode itself. This is the wiring around it,
 * which only App can answer: the "?" is mounted on the screens where the UI
 * needs explaining and on none of the others, and the link out of an
 * explanation lands on the right guide. The issue asked for the main menu to be
 * left alone specifically, so that is asserted rather than assumed.
 *
 * Driving the real App means going through the splash, which is why this file
 * runs on fake timers. Storage is cleared between tests so each one starts on a
 * fresh, unrated board.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { HELP_TOPICS } from "./content/help";

beforeEach(() => {
  localStorage.clear();
  /*
    jsdom has no matchMedia, and App asks for one on its first render to choose
    between the phone tree and the desktop workspace. Answering "no" pins these
    tests to the phone layout, which is the one that ships to an event.
  */
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
  localStorage.clear();
});

/** Past the splash and onto the menu, which holds for a fixed interval. */
function pastSplash() {
  act(() => {
    vi.advanceTimersByTime(3000);
  });
}

describe("contextual help, mounted", () => {
  it("stays off the splash and off the menu", () => {
    render(<App />);
    expect(screen.queryByTestId("help-fab")).toBeNull();

    pastSplash();

    // The menu: a short list of labelled buttons, and no "?" over it.
    expect(document.querySelector(".home-primary")).toBeTruthy();
    expect(screen.queryByTestId("help-fab")).toBeNull();
  });

  it("floats over the board, and explains what is tapped there", () => {
    render(<App />);
    pastSplash();
    fireEvent.click(document.querySelector(".home-primary")!);

    expect(screen.getByTestId("help-fab")).toBeTruthy();

    fireEvent.click(screen.getByTestId("help-fab"));
    fireEvent.click(document.querySelector(".grid")!);

    const grid = HELP_TOPICS.find((t) => t.id === "grid")!;
    expect(screen.getByText(grid.title)).toBeTruthy();
  });

  /*
    The whole route: a card, its guide link, and the guide itself -- with the
    "?" gone, because About & Help is a screen of prose that explains itself.
  */
  it("opens the named guide, and does not follow the reader into it", () => {
    render(<App />);
    pastSplash();
    fireEvent.click(document.querySelector(".home-primary")!);

    fireEvent.click(screen.getByTestId("help-fab"));
    fireEvent.click(document.querySelector(".grid")!);
    const grid = HELP_TOPICS.find((t) => t.id === "grid")!;
    fireEvent.click(screen.getByText(new RegExp(grid.guide!.label, "i")));

    expect(screen.getByTestId("about")).toBeTruthy();
    // Straight into the guide, not the list of guides.
    expect(screen.getByText(/view this guide on github/i)).toBeTruthy();
    expect(document.getElementById(grid.guide!.anchor)).toBeTruthy();
    expect(screen.queryByTestId("help-fab")).toBeNull();
  });
});
