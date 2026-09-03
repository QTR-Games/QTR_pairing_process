// @vitest-environment jsdom
/**
 * Stepping a round back (issue #132): a wrong pick used to mean restarting the
 * whole round. These cover the two halves -- the history stack itself, and the
 * Back control the round header exposes it through.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type Board } from "../model/board";
import { commitPairing, newRound, type LiveState } from "../engine/live";
import { boardMatrix, boardScale } from "../model/board";
import { useLiveHistory } from "../hooks/useLiveHistory";
import { LivePanel } from "./LivePanel";

afterEach(cleanup);

function board(): Board {
  return {
    id: "back-button",
    opponent: "Opponent 03",
    ourPlayers: ["Pete", "Rose"],
    theirPlayers: ["Kev", "Sam"],
    fractions: [
      [0.6, 0.4],
      [0.3, 0.7],
    ],
    scaleId: "five",
    ourTeamFirst: true,
    updatedAt: 0,
  };
}

describe("useLiveHistory", () => {
  it("starts with nothing to undo", () => {
    const { result } = renderHook(() => useLiveHistory(() => newRound(2, true)));
    expect(result.current.canUndo).toBe(false);
  });

  it("steps back to the previous state", () => {
    const { result } = renderHook(() => useLiveHistory(() => newRound(2, true)));
    const first = result.current.live!;

    const b = board();
    const next = commitPairing(boardMatrix(b, boardScale(b)), first, 0, 0, null, null);
    act(() => result.current.advance(next));

    expect(result.current.canUndo).toBe(true);
    expect(result.current.live!.committed).toHaveLength(1);

    act(() => result.current.undo());

    expect(result.current.live).toEqual(first);
    expect(result.current.canUndo).toBe(false);
  });

  it("unwinds several steps in order", () => {
    const { result } = renderHook(() => useLiveHistory(() => newRound(2, true)));
    const a = result.current.live!;
    const b = { ...a, banked: 1 } as LiveState;
    const c = { ...a, banked: 2 } as LiveState;

    act(() => result.current.advance(b));
    act(() => result.current.advance(c));

    act(() => result.current.undo());
    expect(result.current.live!.banked).toBe(1);

    act(() => result.current.undo());
    expect(result.current.live).toEqual(a);
    expect(result.current.canUndo).toBe(false);
  });

  it("drops the stack when the round is reset, so Back cannot cross rounds", () => {
    const { result } = renderHook(() => useLiveHistory(() => newRound(2, true)));
    act(() => result.current.advance({ ...result.current.live!, banked: 5 } as LiveState));
    expect(result.current.canUndo).toBe(true);

    act(() => result.current.reset(newRound(2, true)));

    expect(result.current.canUndo).toBe(false);
  });

  it("ignores undo when there is nothing to step back to", () => {
    const { result } = renderHook(() => useLiveHistory(() => newRound(2, true)));
    const before = result.current.live;
    act(() => result.current.undo());
    expect(result.current.live).toEqual(before);
  });
});

describe("the Back control", () => {
  function Harness() {
    const { live, advance, reset, undo, canUndo } = useLiveHistory(() => newRound(2, true));
    return (
      <LivePanel
        board={board()}
        state={live!}
        onState={advance}
        onReset={() => reset(newRound(2, true))}
        onUndo={undo}
        canUndo={canUndo}
      />
    );
  }

  it("is offered, and starts disabled", () => {
    render(<Harness />);
    expect((screen.getByText("Back") as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables once an action has been taken, and reverses it", () => {
    render(<Harness />);
    expect(screen.getByText(/0 of 2 tables set/)).toBeTruthy();

    fireEvent.click(document.querySelector(".option-main")!);
    const back = screen.getByText("Back") as HTMLButtonElement;
    expect(back.disabled).toBe(false);

    fireEvent.click(back);

    expect(screen.getByText(/0 of 2 tables set/)).toBeTruthy();
    expect((screen.getByText("Back") as HTMLButtonElement).disabled).toBe(true);
  });

  it("is hidden entirely when no handler is supplied", () => {
    render(
      <LivePanel
        board={board()}
        state={newRound(2, true)}
        onState={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.queryByText("Back")).toBeNull();
  });
});
