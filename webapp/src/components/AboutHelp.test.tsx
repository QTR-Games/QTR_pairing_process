// @vitest-environment jsdom
/**
 * About & Help, checked where it navigates.
 *
 * The screen is mostly the guides themselves, whose content is asserted in the
 * docs and DocViewer, not here. What is worth pinning is the movement between
 * the two views it owns: the list opens a guide, the guide comes back to the
 * list, and the outer back control leaves for the menu. Copy is matched loosely
 * so rewording a button does not fail this file.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GUIDES } from "../content/docs";
import { AboutHelp } from "./AboutHelp";

afterEach(cleanup);

describe("AboutHelp", () => {
  it("lists every bundled guide", () => {
    render(<AboutHelp onBack={vi.fn()} />);
    for (const g of GUIDES) {
      expect(screen.getByTestId(`guide-${g.id}`)).toBeTruthy();
    }
  });

  it("returns to the menu from the list, not from a guide", () => {
    const onBack = vi.fn();
    render(<AboutHelp onBack={onBack} />);

    fireEvent.click(screen.getByText(/‹ menu/i));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  /*
    Opening a guide is an in-screen switch, not a call back up to App: onBack
    must stay untouched so the phone's own back gesture is the only thing that
    leaves.
  */
  it("opens a guide and comes back to the list without leaving the screen", () => {
    const onBack = vi.fn();
    render(<AboutHelp onBack={onBack} />);

    fireEvent.click(screen.getByTestId("guide-users-guide"));

    // The detail view offers this guide on GitHub; the list did not.
    const github = screen.getByText(/view this guide on github/i).closest("a");
    expect(github).toBeTruthy();
    expect(github!.getAttribute("href")).toBe(GUIDES[0].href);
    expect(github!.getAttribute("target")).toBe("_blank");
    expect(onBack).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText(/‹ all guides/i));
    // Back on the list: the guide buttons are here again.
    expect(screen.getByTestId("guide-tip-sheet")).toBeTruthy();
    expect(onBack).not.toHaveBeenCalled();
  });
});
