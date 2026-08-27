// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import type { Board } from "../model/board";
import { newRound, type LiveState } from "../engine/live";
import { LivePanel } from "./LivePanel";

afterEach(cleanup);

const FRACTIONS: number[][] = [
  [0.5, 0.9, 0.4, 0.5, 0.6],
  [0.6, 0.5, 0.5, 0.1, 0.5],
  [0.4, 0.5, 0.5, 0.6, 0.8],
  [0.5, 0.6, 0.4, 0.5, 0.5],
  [0.2, 0.5, 0.6, 0.5, 0.5],
];

function board(ourTeamFirst: boolean): Board {
  return {
    id: "surprise",
    opponent: "Opponent 02",
    ourPlayers: ["Pete", "Bokur", "Sam", "Ana", "Rue"],
    theirPlayers: ["Kev", "Mo", "Jo", "Tam", "Wes"],
    fractions: FRACTIONS,
    scaleId: "five",
    ourTeamFirst,
    updatedAt: 0,
  };
}

function Harness({
  b,
  mode,
  threshold,
  initialState,
}: {
  b: Board;
  mode: "off" | "on";
  threshold: number;
  initialState?: LiveState;
}) {
  const [state, setState] = useState<LiveState>(
    () => initialState ?? newRound(b.ourPlayers.length, b.ourTeamFirst),
  );
  return (
    <LivePanel
      board={b}
      state={state}
      onState={setState}
      onReset={() => setState(newRound(b.ourPlayers.length, b.ourTeamFirst))}
      surpriseMode={mode}
      surpriseRegretThreshold={threshold}
    />
  );
}

function stateAtTheirPick(): LiveState {
  // One legal offer pair (our players 2 and 3) against their attacker 1.
  return {
    ourPool: (1 << 2) | (1 << 3),
    theirPool: (1 << 0) | (1 << 4),
    attacker: 1,
    attackerSide: "their",
    banked: 0,
    committed: [],
  };
}

function tapOpponentOffModelPick(container: HTMLElement): void {
  const picks = Array.from(container.querySelectorAll("button.pick"));
  if (picks.length !== 2) throw new Error("expected exactly two pick buttons");
  const values = picks.map((p) => Number(p.querySelector(".pick-value")?.textContent ?? "NaN"));
  if (!Number.isFinite(values[0]) || !Number.isFinite(values[1])) {
    throw new Error("missing numeric pick values");
  }
  if (Math.abs(values[0] - values[1]) < 1e-9) throw new Error("need non-equal pick values");
  // They should minimise our projected total; the higher value is the off-model pick.
  const offModel = values[0] > values[1] ? picks[0] : picks[1];
  fireEvent.click(offModel);
}

describe("LivePanel surprise alerts", () => {
  it("raises an anomaly banner when the opponent deviates and the feature is on", () => {
    const { container } = render(
      <Harness b={board(false)} mode="on" threshold={0} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container);

    const flag = container.querySelector(".surprise-flag");
    expect(flag).not.toBeNull();
    expect(flag?.textContent ?? "").toContain("suspiciously outside expectations");
  });

  it("stays quiet when the feature is off", () => {
    const { container } = render(
      <Harness b={board(false)} mode="off" threshold={0} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container);
    expect(container.querySelector(".surprise-flag")).toBeNull();
  });

  it("respects the configured threshold", () => {
    const { container } = render(
      <Harness b={board(false)} mode="on" threshold={99} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container);
    expect(container.querySelector(".surprise-flag")).toBeNull();
  });
});
