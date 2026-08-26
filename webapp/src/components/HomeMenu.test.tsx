// @vitest-environment jsdom
/**
 * The menu, checked where it makes decisions.
 *
 * Most of this screen is static markup and is not worth asserting on. Two
 * parts are not:
 *
 *   - the primary action, which picks one of three labels and one of two
 *     callbacks from the live round and the saved list. Getting this wrong
 *     sends someone mid-round to a fresh grid.
 *   - the links, one of which used to be deliberately absent. `LINKS.beer` now
 *     has a real Ko-fi URL, but the assertions stay pinned to the constants so
 *     that blanking either one in brand.ts still exercises the hidden path.
 *
 * Copy is asserted loosely -- by the opponent's name, not by the sentence
 * around it -- so rewording the labels does not fail this file.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LINKS } from "../brand";
import { emptyBoard, type Board } from "../model/board";
import { HomeMenu } from "./HomeMenu";

afterEach(cleanup);

function board(opponent: string): Board {
  return { ...emptyBoard(), opponent };
}

/** Every prop supplied, so each test overrides only what it is about. */
function renderMenu(over: Partial<Parameters<typeof HomeMenu>[0]> = {}) {
  const props = {
    liveOpponent: null,
    lastBoard: null,
    boardCount: 0,
    dodgeMode: "onDemand" as const,
    onDodgeMode: vi.fn(),
    onResume: vi.fn(),
    onContinue: vi.fn(),
    onBoards: vi.fn(),
    onRestored: vi.fn(),
    ...over,
  };
  render(<HomeMenu {...props} />);
  return props;
}

/** The primary action is the first button on the screen, whatever it says. */
function primary(): HTMLButtonElement {
  const el = document.querySelector(".home-primary");
  expect(el).toBeTruthy();
  return el as HTMLButtonElement;
}

describe("HomeMenu primary action", () => {
  it("names the live opponent and resumes the round", () => {
    const props = renderMenu({
      liveOpponent: "Brass Ravens",
      lastBoard: board("Some Other Lot"),
      boardCount: 2,
    });

    expect(primary().textContent).toContain("Brass Ravens");

    fireEvent.click(primary());
    expect(props.onResume).toHaveBeenCalledTimes(1);
    expect(props.onContinue).not.toHaveBeenCalled();
  });

  /*
    A live round outranks the saved list even when a newer board exists. This
    is the case that costs the most to get wrong: someone is standing at the
    table halfway through nominating.
  */
  it("prefers the live round over the most recent board", () => {
    renderMenu({
      liveOpponent: "Brass Ravens",
      lastBoard: board("Some Other Lot"),
      boardCount: 2,
    });

    expect(primary().textContent).not.toContain("Some Other Lot");
  });

  it("names the last board when nothing is live", () => {
    const props = renderMenu({ lastBoard: board("Iron Wolves"), boardCount: 1 });

    expect(primary().textContent).toContain("Iron Wolves");

    fireEvent.click(primary());
    expect(props.onContinue).toHaveBeenCalledTimes(1);
    expect(props.onResume).not.toHaveBeenCalled();
  });

  /*
    An unnamed board would otherwise produce a button reading "Open " with
    nothing after it.
  */
  it("falls back to a generic label for an unnamed board", () => {
    const props = renderMenu({ lastBoard: board("   "), boardCount: 1 });

    expect(primary().textContent).toContain("Start a new board");

    fireEvent.click(primary());
    expect(props.onContinue).toHaveBeenCalledTimes(1);
  });

  it("offers a new board when nothing is saved", () => {
    renderMenu();
    expect(primary().textContent).toContain("Start a new board");
  });
});

describe("HomeMenu links", () => {
  /*
    Still pinned to the constant rather than to a hard-coded true, so that
    blanking either link in brand.ts keeps this file honest instead of turning
    it into a failure to go and delete.
  */
  it("offers the beer link, opened away from the app", () => {
    renderMenu();

    const links = Array.from(document.querySelectorAll(".home-links a"));
    const beer = links.find((a) => /beer/i.test(a.textContent ?? "")) ?? null;

    expect(Boolean(beer)).toBe(Boolean(LINKS.beer));
    if (!beer) return;

    expect(beer.getAttribute("href")).toBe(LINKS.beer);
    // A round in progress lives in memory; navigating this tab away loses it.
    expect(beer.getAttribute("target")).toBe("_blank");
    expect(beer.getAttribute("rel")).toContain("noreferrer");
  });

  it("offers the bug link, opened away from the app", () => {
    renderMenu();

    const bug = screen.getByText(/log a bug/i).closest("a");
    expect(bug).toBeTruthy();
    expect(bug!.getAttribute("href")).toBe(LINKS.bugs);
    // A round in progress lives in memory; navigating this tab away loses it.
    expect(bug!.getAttribute("target")).toBe("_blank");
    expect(bug!.getAttribute("rel")).toContain("noreferrer");
  });
});

describe("HomeMenu settings", () => {
  it("reports a change of dodge mode rather than holding it locally", () => {
    const props = renderMenu({ dodgeMode: "off" });

    const select = document.querySelector(".home-body select") as HTMLSelectElement;
    expect(select.value).toBe("off");

    fireEvent.change(select, { target: { value: "always" } });
    expect(props.onDodgeMode).toHaveBeenCalledWith("always");
    // Still "off": App owns this, and the menu only reflects what it is told.
    expect((document.querySelector(".home-body select") as HTMLSelectElement).value).toBe(
      "off",
    );
  });

  it("counts the saved boards on the way to the list", () => {
    const props = renderMenu({ boardCount: 3 });

    const saved = screen.getByText(/saved boards/i);
    expect(saved.textContent).toContain("3");

    fireEvent.click(saved);
    expect(props.onBoards).toHaveBeenCalledTimes(1);
  });
});
