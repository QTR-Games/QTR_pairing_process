// @vitest-environment jsdom
/**
 * The contextual help overlay, checked where it is risky.
 *
 * Two things matter here and nothing else really does. The first is that help
 * mode explains instead of acting: it runs over screens where a stray tap rates
 * a matchup or commits a pairing, so the test that a tapped control's own
 * handler never fires is the reason this file exists. The second is that the
 * lookup walks up from whatever was actually hit to the nearest `data-help`
 * ancestor, because most of the tagged things in the app are containers with
 * text and buttons inside them.
 *
 * Copy is matched loosely -- titles come from content/help.ts and rewording one
 * should not fail this file.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HELP_TOPICS } from "../content/help";
import { HelpLayer } from "./HelpOverlay";

afterEach(cleanup);

const GRID = HELP_TOPICS.find((t) => t.id === "grid")!;

/** A stand-in for a screen: a tagged container with a live control inside it. */
function Harness({ onTap, onOpenGuide }: { onTap: () => void; onOpenGuide?: () => void }) {
  return (
    <>
      <div data-help="grid">
        <button onClick={onTap}>Rate this cell</button>
      </div>
      <div>
        <button onClick={onTap}>Untagged</button>
      </div>
      <HelpLayer onOpenGuide={onOpenGuide ?? vi.fn()} />
    </>
  );
}

function enterHelpMode() {
  fireEvent.click(screen.getByTestId("help-fab"));
}

describe("HelpLayer", () => {
  it("is just a ? until it is asked", () => {
    render(<Harness onTap={vi.fn()} />);
    expect(screen.getByTestId("help-fab")).toBeTruthy();
    expect(screen.queryByTestId("help-card")).toBeNull();
    expect(screen.queryByTestId("help-scrim")).toBeNull();
  });

  it("dims the screen and invites a tap", () => {
    render(<Harness onTap={vi.fn()} />);
    enterHelpMode();

    expect(screen.getByTestId("help-scrim")).toBeTruthy();
    expect(screen.getByTestId("help-card")).toBeTruthy();
    expect(screen.getByTestId("help-fab").getAttribute("aria-pressed")).toBe("true");
  });

  /*
    The whole point. A control tapped in help mode is explained, not pressed:
    the tap lands on the button, the explanation comes from the tagged element
    around it, and the button's own handler never runs.
  */
  it("explains what was tapped without running it", () => {
    const onTap = vi.fn();
    render(<Harness onTap={onTap} />);
    enterHelpMode();

    fireEvent.click(screen.getByText("Rate this cell"));

    expect(onTap).not.toHaveBeenCalled();
    expect(screen.getByText(GRID.title)).toBeTruthy();
  });

  /* A phone produces pointerdown, and a long-press starts with one. */
  it("answers a pointer press too, and only once", () => {
    const onTap = vi.fn();
    render(<Harness onTap={onTap} />);
    enterHelpMode();

    const cell = screen.getByText("Rate this cell");
    fireEvent.pointerDown(cell, { button: 0 });
    fireEvent.click(cell);

    expect(onTap).not.toHaveBeenCalled();
    expect(screen.getAllByText(GRID.title)).toHaveLength(1);
  });

  it("says so plainly when there is nothing written for what was tapped", () => {
    render(<Harness onTap={vi.fn()} />);
    enterHelpMode();

    fireEvent.click(screen.getByText("Untagged"));

    expect(screen.getByText(/nothing to explain/i)).toBeTruthy();
  });

  it("offers the guide section for a topic that has one, and leaves on the way", () => {
    const onOpenGuide = vi.fn();
    render(<Harness onTap={vi.fn()} onOpenGuide={onOpenGuide} />);
    enterHelpMode();

    fireEvent.click(screen.getByText("Rate this cell"));
    fireEvent.click(screen.getByText(new RegExp(GRID.guide!.label, "i")));

    expect(onOpenGuide).toHaveBeenCalledWith(GRID.guide!.id, GRID.guide!.anchor);
    // Help mode is over: the reader is being sent to another screen.
    expect(screen.queryByTestId("help-scrim")).toBeNull();
  });

  it("hands the screen back when the ? is pressed again", () => {
    const onTap = vi.fn();
    render(<Harness onTap={onTap} />);
    enterHelpMode();
    fireEvent.click(screen.getByTestId("help-fab"));

    expect(screen.queryByTestId("help-card")).toBeNull();

    fireEvent.click(screen.getByText("Rate this cell"));
    expect(onTap).toHaveBeenCalledTimes(1);
  });

  it("hands the screen back on Escape", () => {
    render(<Harness onTap={vi.fn()} />);
    enterHelpMode();

    fireEvent.keyDown(document.body, { key: "Escape" });

    expect(screen.queryByTestId("help-card")).toBeNull();
  });

  /*
    Its own Done button has to survive the same swallowing that stops every
    other tap, or help mode would be a trap on a phone with no Escape key.
  */
  it("closes from its own Done button", () => {
    render(<Harness onTap={vi.fn()} />);
    enterHelpMode();

    fireEvent.click(screen.getByText(/^done$/i));

    expect(screen.queryByTestId("help-card")).toBeNull();
    expect(screen.getByTestId("help-fab").getAttribute("aria-pressed")).toBe("false");
  });

  it("stops listening once it is unmounted", () => {
    const view = render(<Harness onTap={vi.fn()} />);
    enterHelpMode();
    view.unmount();

    const after = document.createElement("button");
    document.body.appendChild(after);
    const spy = vi.fn();
    after.addEventListener("click", spy);
    fireEvent.click(after);

    // A listener left behind on document would still be swallowing this.
    expect(spy).toHaveBeenCalledTimes(1);
    after.remove();
  });
});
