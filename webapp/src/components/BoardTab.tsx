import { useMemo } from "react";
import { Grid, Rosters } from "./Grid";
import { useVerdictModel, VerdictHeadline, VerdictCards } from "./Verdict";
import { boardMatrix, boardScale, isRated, type Board } from "../model/board";
import { SCALES } from "../model/scale";
import { openingChoice } from "../engine/protocol";
import type { DodgeMode } from "../model/settings";

interface Props {
  board: Board;
  onBoardChange: (b: Board) => void;
  highlight: Set<string>;
  onHighlight: (cells: Set<string>) => void;
  lockedCells: Set<string>;
  dodgeMode: DodgeMode;
  onStartRound: () => void;
}

/**
 * The phone Board tab, in one fixed order.
 *
 * The reading, the controls, the rosters, the grid and the follow-up cards used
 * to swap places depending on whether the board was rated. That reorder is gone:
 * the order is now the same on a blank board and a full one, so nothing shifts
 * under a captain's thumb mid-rating. The grid is pinned with `position: sticky`
 * (see `.board-grid-sticky`) so it stays on screen while the cards below it
 * scroll -- the whole point of the fixed order is that the sheet you are tapping
 * never leaves the viewport.
 *
 * The verdict is split into its two halves -- the headline reading above the
 * grid, the follow-up cards below it -- with the analysis run exactly once via
 * `useVerdictModel`. Rendering `<Verdict>` twice would double every solve it
 * makes; the model is computed here and handed to both halves instead.
 */
export function BoardTab({
  board,
  onBoardChange,
  highlight,
  onHighlight,
  lockedCells,
  dodgeMode,
  onStartRound,
}: Props) {
  const scale = boardScale(board);
  const rated = isRated(board);
  const model = useVerdictModel({ board, onBoardChange, dodgeMode });

  /**
   * Step 1 of the protocol -- who nominates first -- is decided by a dice-off
   * before any player is named, and it is the one decision on this screen that
   * cannot be walked back later in the round. It is also the cheapest: it costs
   * nothing to get right and, measured across all 31 saved boards, receiving is
   * worth a mean 0.58 points over opening and never less than zero.
   *
   * The engine still computes it per board rather than printing a fixed answer,
   * because the rule is a parity effect rather than a law -- see the note above
   * `openingChoice` in engine/protocol.ts.
   */
  const opening = useMemo(
    () => (rated ? openingChoice(boardMatrix(board, scale)) : null),
    [board, scale, rated],
  );

  return (
    <>
      <section className="verdict">
        <VerdictHeadline model={model} />
      </section>

      <div className="controls">
        <label className="field inline">
          <span>Scale</span>
          <select
            // Resolved id, not the stored one -- see the matching note in
            // DesktopWorkspace. An unrecognised scaleId falls back to 1-5
            // everywhere except here, where it would show "Stoplight".
            value={scale.id}
            onChange={(e) => onBoardChange({ ...board, scaleId: e.target.value })}
          >
            {SCALES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <p className="hint">{scale.hint}</p>

        <label className="field inline">
          <span>Who puts a player up first?</span>
          <select
            value={board.ourTeamFirst ? "us" : "them"}
            onChange={(e) => onBoardChange({ ...board, ourTeamFirst: e.target.value === "us" })}
          >
            <option value="us">We do</option>
            <option value="them">They do</option>
          </select>
        </label>
        {/*
          Silent when the two floors are level, because a recommendation
          worth nothing is just one more thing to read at a table. Shown
          as a button when it disagrees with the dropdown so the fix is
          one tap rather than a second decision.
        */}
        {opening && opening.gain >= 0.005 && (
          opening.weOpen === board.ourTeamFirst ? (
            <p className="hint">
              If you win the dice-off, {opening.weOpen ? "go first" : "make them go first"}
              {" "}-- worth {opening.gain.toFixed(2)} here. Already set.
            </p>
          ) : (
            <button
              className="ghost wide"
              onClick={() => onBoardChange({ ...board, ourTeamFirst: opening.weOpen })}
            >
              Win the dice-off and{" "}
              {opening.weOpen ? "go first" : "make them go first"} -- worth{" "}
              {opening.gain.toFixed(2)}. Tap to set.
            </button>
          )
        )}
      </div>

      <Rosters board={board} onChange={onBoardChange} />

      {/*
        The sheet the captain is tapping stays on screen while the follow-up
        cards below scroll. Opaque background so the transparent gaps in the
        grid's border-spacing do not show the cards sliding underneath.
      */}
      <div className="board-grid-sticky">
        <Grid board={board} onChange={onBoardChange} highlight={highlight} locked={lockedCells} />
      </div>

      {model.rated && (
        <section className="verdict">
          <VerdictCards model={model} onHighlight={onHighlight} />
        </section>
      )}

      {/*
        Start the round once you have rated -- at the very bottom, after the
        grid and the reading, because it is the last thing you do on this
        screen rather than the first.
      */}
      <button className="primary wide" onClick={onStartRound}>
        Start the round
      </button>
    </>
  );
}
