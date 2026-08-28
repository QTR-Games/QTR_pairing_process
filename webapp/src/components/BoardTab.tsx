import { useMemo } from "react";
import { Grid, Rosters } from "./Grid";
import { useVerdictModel, VerdictHeadline, VerdictCards } from "./Verdict";
import { boardMatrix, boardScale, isRated, type Board } from "../model/board";
import { SCALES } from "../model/scale";
import { dodgeCellChance } from "../engine/avoidance";
import { cellOutlooks, evenThreshold } from "../engine/boardAnalysis";
import { openingChoice } from "../engine/protocol";
import { toWinProbability } from "../engine/winProbability";
import { pct } from "../model/format";
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
        <Grid
          board={board}
          onChange={onBoardChange}
          highlight={highlight}
          locked={lockedCells}
          cellInfo={(ours, theirs) => <CellAnalysis board={board} ours={ours} theirs={theirs} />}
        />
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

/**
 * The per-cell info sheet body, shown when a captain long-presses a grid cell.
 *
 * The desktop paints two overlays across all 25 cells at once -- what each
 * opening costs (in points) and what refusing each matchup costs (in round-win
 * chance). A phone has no room for that, so a hold on one cell shows both
 * figures for just that matchup here. Kept out of `Grid` so the grid stays
 * presentational and pulls in no engine code; the phone Board tab owns the
 * analysis and hands it in through `cellInfo`.
 *
 * Everything is computed in a single `useMemo` that runs when the sheet mounts
 * -- which is only when a hold fires -- so the dodge solve, the one expensive
 * step, never runs while ratings are being typed. It prices this single cell
 * via `dodgeCellChance` rather than the whole board, ~12 ms instead of ~293.
 *
 * The two figures stay in their own units on purpose: the opening cost is a
 * points total, the dodge a probability, and the two must never be added or
 * shown as one number (see the note on `ChancePrice` in avoidance.ts).
 */
function CellAnalysis({ board, ours, theirs }: { board: Board; ours: number; theirs: number }) {
  const scale = boardScale(board);
  const analysis = useMemo(() => {
    const matrix = boardMatrix(board, scale);
    const rating = matrix[ours][theirs];
    const winChance = toWinProbability(rating, scale.min, scale.max);
    if (!isRated(board)) return { rating, winChance, rated: false as const };
    const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);
    const outlooks = cellOutlooks(matrix, tau);
    let bestFloor = -Infinity;
    for (const o of outlooks.values()) bestFloor = Math.max(bestFloor, o.floor);
    const outlook = outlooks.get(`${ours},${theirs}`)!;
    const cost = bestFloor - outlook.floor;
    const dodge = dodgeCellChance(matrix, { ours, theirs }, scale.min, scale.max, board.ourTeamFirst);
    return { rating, winChance, rated: true as const, floor: outlook.floor, cost, dodge };
  }, [board, scale, ours, theirs]);

  return (
    <div className="cell-info">
      <p className="cell-info-rating">
        Rated <strong>{analysis.rating}</strong> &mdash; about {pct(analysis.winChance)} to take
        this game.
      </p>
      {!analysis.rated ? (
        <p className="sheet-hint">Rate the board to price this matchup.</p>
      ) : (
        <>
          <div className="cell-info-row">
            <span className="cell-info-label">What this opening costs</span>
            <span className="cell-info-value">
              {analysis.cost < 1e-9 ? (
                <>
                  Guaranteed {analysis.floor.toFixed(1)} &mdash;{" "}
                  <strong>best on the board</strong>
                </>
              ) : (
                <>
                  Guaranteed {analysis.floor.toFixed(1)}, giving up {analysis.cost.toFixed(1)}{" "}
                  against the best opening
                </>
              )}
            </span>
          </div>
          <div className="cell-info-row">
            <span className="cell-info-label">Refusing this matchup</span>
            <span className="cell-info-value">
              {analysis.dodge.price === null ? (
                <>
                  <strong>forced</strong> &mdash; no line of play refuses it
                </>
              ) : analysis.dodge.free ? (
                <>
                  <strong>free</strong> &mdash; the protocol dodges it for nothing
                </>
              ) : (
                <>
                  costs <strong>{pct(analysis.dodge.price)}</strong> of round-win chance
                </>
              )}
            </span>
          </div>
          <p className="sheet-hint">
            Two currencies on purpose: the opening cost is in points, the dodge in round-win
            chance. A high dodge price on a cell you rated badly is the matchup you are stuck with.
          </p>
        </>
      )}
    </div>
  );
}
