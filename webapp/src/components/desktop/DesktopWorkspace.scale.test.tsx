// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { DesktopWorkspace } from "./DesktopWorkspace";
import { emptyBoard, boardScale, type Board } from "../../model/board";
import { SCALES } from "../../model/scale";

afterEach(cleanup);

/**
 * The scale picker must never disagree with the grid beside it.
 *
 * Found by driving the real app in a browser: a board whose stored scaleId was
 * "1-5" -- the *label* of the 1-5 scale, not its id, which is "five" -- rendered
 * a 1-5 grid under a picker reading "Stoplight". scaleById falls back to 1-5 for
 * an id it does not recognise, so every consumer resolved correctly except the
 * <select>, which matched no <option> and so displayed the first one.
 *
 * That is the worst shape this bug could take at an event: "Stoplight" describes
 * a 1-3 scale, so the picker actively misreports the meaning of every number on
 * screen rather than merely looking wrong.
 */
const noop = () => {};

function renderWorkspace(board: Board) {
  return render(
    <DesktopWorkspace
      board={board}
      onBoard={noop}
      live={null}
      onLive={noop}
      onStartRound={noop}
      dodgeMode="onDemand"
      onDodgeMode={noop}
      adviceLevel="full"
      onAdviceLevel={noop}
      surpriseMode="off"
      onSurpriseMode={noop}
      surpriseRegretThreshold={0}
      onSurpriseRegretThreshold={noop}
    />,
  );
}

/** The picker, identified by an option only it carries. */
function scalePicker(): HTMLSelectElement {
  const all = screen.getAllByRole("combobox") as HTMLSelectElement[];
  const found = all.find((s) => s.textContent?.includes("Stoplight"));
  if (!found) throw new Error("scale picker not rendered");
  return found;
}

describe("scale picker", () => {
  it("shows the scale the rest of the screen is actually using", () => {
    const board = { ...emptyBoard("five"), scaleId: "1-5" };
    renderWorkspace(board);

    // What every other consumer resolves to.
    expect(boardScale(board).id).toBe("five");
    // What the picker shows. Before the fix this was "stoplight".
    expect(scalePicker().value).toBe("five");
  });

  it("round-trips every real scale id unchanged", () => {
    for (const s of SCALES) {
      renderWorkspace({ ...emptyBoard("five"), scaleId: s.id });
      expect(scalePicker().value).toBe(s.id);
      cleanup();
    }
  });

  it("never leaves the picker on a value the board does not resolve to", () => {
    // Ids a legacy board or a hand-edited backup could plausibly carry: the
    // labels, plus an outright unknown.
    const suspect = [...SCALES.map((s) => s.label), "", "1-5", "linear", "??"];
    for (const scaleId of suspect) {
      const board = { ...emptyBoard("five"), scaleId };
      renderWorkspace(board);
      expect(scalePicker().value).toBe(boardScale(board).id);
      cleanup();
    }
  });
});
