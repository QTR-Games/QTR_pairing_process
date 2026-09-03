// @vitest-environment jsdom
/**
 * Table tracking (issue #134): once a pairing is locked in, the round can
 * pause on a popup asking which table it went to, with a skip button for a
 * captain who is not tracking tables. Off by default behaviour is covered by
 * every other LivePanel test in this suite, which never sets the prop and
 * must see the exact same tap-and-advance flow it always has.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type Board } from "../model/board";
import { type LiveState } from "../engine/live";
import { LivePanel } from "./LivePanel";

afterEach(cleanup);

function board(): Board {
  return {
    id: "table-tracking",
    opponent: "Opponent 02",
    ourPlayers: ["Pete"],
    theirPlayers: ["Kev"],
    fractions: [[0.6]],
    scaleId: "five",
    ourTeamFirst: true,
    updatedAt: 0,
  };
}

/** Already past the nomination step, sitting on the one legal (forced) pairing. */
function forcedState(): LiveState {
  return {
    ourPool: 0,
    theirPool: 1,
    attacker: 0,
    attackerSide: "our",
    banked: 0,
    committed: [],
  };
}

function Harness({ tableTracking }: { tableTracking?: "on" | "off" }) {
  const [state, setState] = useState<LiveState>(forcedState());
  return (
    <LivePanel
      board={board()}
      state={state}
      onState={setState}
      onReset={() => setState(forcedState())}
      tableTracking={tableTracking}
    />
  );
}

/** The "Tables set" panel, once the round has committed the one pairing. */
function committedPanel(): HTMLElement {
  const el = document.querySelector(".committed");
  expect(el).toBeTruthy();
  return el as HTMLElement;
}

describe("table tracking off (the default)", () => {
  it("commits the pairing immediately, with no popup", () => {
    render(<Harness />);
    fireEvent.click(document.querySelector(".option-main")!);

    expect(screen.queryByText(/Which table/i)).toBeNull();
    expect(within(committedPanel()).getByText("Tables set")).toBeTruthy();
    expect(within(committedPanel()).getByText(/Pete vs Kev/)).toBeTruthy();
  });
});

describe("table tracking on", () => {
  it("holds the round on a table popup after the pairing locks in", () => {
    render(<Harness tableTracking="on" />);
    fireEvent.click(document.querySelector(".option-main")!);

    // The prompt is up, and the round has not yet advanced to "done" behind it.
    expect(screen.getByText(/Which table/i)).toBeTruthy();
  });

  it("records the typed table once confirmed", () => {
    render(<Harness tableTracking="on" />);
    fireEvent.click(document.querySelector(".option-main")!);

    fireEvent.change(screen.getByPlaceholderText("e.g. 5"), { target: { value: "7" } });
    fireEvent.click(screen.getByText("Set table"));

    expect(screen.queryByText(/Which table/i)).toBeNull();
    expect(within(committedPanel()).getByText(/Table 7/)).toBeTruthy();
  });

  it("leaves the table blank when skipped", () => {
    render(<Harness tableTracking="on" />);
    fireEvent.click(document.querySelector(".option-main")!);

    fireEvent.click(screen.getByText("Skip"));

    expect(screen.queryByText(/Which table/i)).toBeNull();
    expect(within(committedPanel()).getByText(/Pete vs Kev/)).toBeTruthy();
    expect(within(committedPanel()).queryByText(/— Table/)).toBeNull();
  });

  it("copies the committed list to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<Harness tableTracking="on" />);
    fireEvent.click(document.querySelector(".option-main")!);
    fireEvent.change(screen.getByPlaceholderText("e.g. 5"), { target: { value: "7" } });
    fireEvent.click(screen.getByText("Set table"));

    fireEvent.click(screen.getByLabelText("Copy tables set to clipboard"));

    await Promise.resolve();
    expect(writeText).toHaveBeenCalledWith("Pete vs Kev — Table 7");
  });
});
