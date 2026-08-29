// @vitest-environment jsdom
import { cleanup, fireEvent, render, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { boardMatrix, boardScale, type Board } from "../model/board";
import { newRound, pickOptions, type LiveState } from "../engine/live";
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

function tapOpponentOffModelPick(container: HTMLElement, b: Board): void {
  const picks = Array.from(container.querySelectorAll<HTMLButtonElement>("button.pick"));
  if (picks.length !== 2) throw new Error("expected exactly two pick buttons");

  // Which half is off-model is a property of the search, not of the rounded
  // percentage on screen: two distinct floors can print the same whole percent.
  // They hold the attacker here, so they minimise our total -- the higher-value
  // half is the one the model says they should not take.
  const s = stateAtTheirPick();
  const matrix = boardMatrix(b, boardScale(b));
  const options = pickOptions(matrix, s, [2, 3]);
  if (Math.abs(options[0].value - options[1].value) < 1e-9) {
    throw new Error("need non-equal pick values");
  }
  const offModelPlayer = options[0].value > options[1].value ? options[0].player : options[1].player;
  const offModelName = b.ourPlayers[offModelPlayer];

  const button = picks.find((p) => within(p).queryByText(new RegExp(offModelName)));
  if (!button) throw new Error("could not find the off-model pick button");
  fireEvent.click(button);
}

describe("LivePanel surprise alerts", () => {
  it("raises an anomaly banner when the opponent deviates and the feature is on", () => {
    const { container } = render(
      <Harness b={board(false)} mode="on" threshold={0} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container, board(false));

    const flag = container.querySelector(".surprise-flag");
    expect(flag).not.toBeNull();
    expect(flag?.textContent ?? "").toContain("suspiciously outside expectations");
  });

  it("stays quiet when the feature is off", () => {
    const { container } = render(
      <Harness b={board(false)} mode="off" threshold={0} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container, board(false));
    expect(container.querySelector(".surprise-flag")).toBeNull();
  });

  it("respects the configured threshold", () => {
    const { container } = render(
      <Harness b={board(false)} mode="on" threshold={99} initialState={stateAtTheirPick()} />,
    );
    tapOpponentOffModelPick(container, board(false));
    expect(container.querySelector(".surprise-flag")).toBeNull();
  });
});
