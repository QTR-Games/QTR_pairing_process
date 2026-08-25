import { useMemo, useState } from "react";
import { dodgeMapChance } from "../../engine/avoidance";
import { evenThreshold } from "../../engine/boardAnalysis";
import type { Matrix } from "../../engine/boardAnalysis";
import type { LiveState } from "../../engine/live";
import { openingChoice } from "../../engine/protocol";
import { boardMatrix, boardScale, isRated, type Board } from "../../model/board";
import { SCALES } from "../../model/scale";
import { DODGE_MODES, type DodgeMode } from "../../model/settings";
import { Grid, Rosters } from "../Grid";
import { LivePanel } from "../LivePanel";
import { Verdict } from "../Verdict";
import { Currencies } from "./Currencies";
import { ProtocolTree } from "./ProtocolTree";
import { ReachPanel } from "./ReachPanel";

interface Props {
  board: Board;
  onBoard: (b: Board) => void;
  live: LiveState | null;
  onLive: (s: LiveState | null) => void;
  onStartRound: () => void;
  dodgeMode: DodgeMode;
  onDodgeMode: (m: DodgeMode) => void;
}

/**
 * The laptop layout.
 *
 * The phone app is three tabs because a 390px column can hold one of the three
 * things you want at once. Every tab switch at a table is a moment where you
 * are looking at the wrong thing, and the round is a conversation that does not
 * pause while you find the right screen.
 *
 * A 1920x1080 screen holds all three at once, so it does. The sheet, the
 * reading, the reach analysis and the protocol tree are on screen together and
 * stay together while a round is running -- the live panel appears beside the
 * sheet rather than instead of it.
 *
 * Nothing here is reachable below 1024px. `App` picks between this and the
 * untouched phone tree on a media query, so the build that goes to an event on
 * a phone renders exactly the components it did before this file existed.
 */
export function DesktopWorkspace({
  board,
  onBoard,
  live,
  onLive,
  onStartRound,
  dodgeMode,
  onDodgeMode,
}: Props) {
  const scale = boardScale(board);
  const rated = isRated(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);

  const [highlight, setHighlight] = useState<Set<string>>(new Set());
  const [heat, setHeat] = useState(false);

  const lockedCells = useMemo(() => {
    const s = new Set<string>();
    live?.committed.forEach((c) => s.add(`${c.ours}-${c.theirs}`));
    return s;
  }, [live]);

  const opening = useMemo(() => (rated ? openingChoice(matrix) : null), [matrix, rated]);

  /**
   * Every cell on the board, priced by what refusing it costs.
   *
   * Behind a switch, and off by default, for one measured reason: this is
   * 25 constrained searches under the probability solver and it takes 293 ms
   * on a 5x5. That is fine for a deliberate click and unacceptable behind a
   * keystroke, so it never runs while a rating is being typed.
   *
   * Priced in round-win chance rather than points on purpose. The points-valued
   * `dodgeMap` reads 0.000 for the worst cell on all 31 saved boards -- a flat
   * heat map is not a heat map -- because a total barely moves when you change
   * which bad cell you eat. Under this currency the worst cell is worth 8.2%
   * on average and 15.9% at the extreme, and about 11 of the 25 cells price
   * above zero on a typical board.
   */
  const heatMap = useMemo(() => {
    if (!heat || !rated) return null;
    const prices = dodgeMapChance(matrix, scale.min, scale.max, board.ourTeamFirst);
    const byCell = new Map<string, (typeof prices)[number]>();
    let max = 0;
    for (const p of prices) {
      byCell.set(`${p.cell.ours}-${p.cell.theirs}`, p);
      if (p.price !== null && p.price > max) max = p.price;
    }
    return { byCell, max };
  }, [heat, rated, matrix, scale.min, scale.max, board.ourTeamFirst]);

  const overlay = heatMap
    ? (i: number, j: number) => {
        const p = heatMap.byCell.get(`${i}-${j}`);
        if (!p) return null;
        if (p.price === null) {
          // No strategy refuses this cell. Worth flagging louder than a price.
          return <span className="heat pinned">forced</span>;
        }
        if (p.price <= 0) return <span className="heat free">free</span>;
        const share = heatMap.max > 0 ? p.price / heatMap.max : 0;
        return (
          <span className="heat cost">
            <span className="heat-bar" style={{ width: `${Math.round(share * 100)}%` }} />
            <span className="heat-num">{(p.price * 100).toFixed(1)}%</span>
          </span>
        );
      }
    : undefined;

  return (
    <div className="desk">
      <div className="desk-col desk-read">
        <Currencies board={board} scale={scale} matrix={matrix} tau={tau} />
        <Verdict board={board} onHighlight={setHighlight} dodgeMode={dodgeMode} />
      </div>

      <div className="desk-col desk-sheet">
        <section className="panel">
          <div className="panel-head">
            <h2>Matchup sheet</h2>
            <label className="switch">
              <input type="checkbox" checked={heat} onChange={(e) => setHeat(e.target.checked)} />
              <span>Price every dodge</span>
            </label>
          </div>
          <Grid
            board={board}
            onChange={onBoard}
            highlight={highlight}
            locked={lockedCells}
            overlay={overlay}
          />
          {heat && (
            <p className="hint">
              Each cell shows what refusing that matchup costs, in round-win
              chance. <strong>free</strong> means the protocol lets you dodge it
              for nothing; <strong>forced</strong> means no line of play refuses
              it at all. Read it against the rating: a high price on a cell you
              rated well only says the cell is good. The cells worth finding are
              the ones you rated badly that still price high -- those are the
              matchups you are stuck with. Recomputed on demand, about 293 ms.
            </p>
          )}
          {!heat && (
            <p className="hint">
              The phone build prices only the single worst matchup, because
              pricing all 25 costs 293 ms and there is nowhere to put the answer.
              There is room here.
            </p>
          )}
        </section>

        {rated && (
          <ProtocolTree board={board} matrix={matrix} tau={tau} onHighlight={setHighlight} />
        )}
      </div>

      <div className="desk-col desk-analysis">
        {live ? (
          <section className="panel">
            <LivePanel board={board} state={live} onState={onLive} onReset={onStartRound} />
          </section>
        ) : null}

        {rated && (
          <ReachPanel
            board={board}
            scale={scale}
            matrix={matrix}
            onHighlight={setHighlight}
          />
        )}

        <section className="panel">
          <h2>Setup</h2>
          <div className="desk-controls">
            <label className="field inline">
              <span>Scale</span>
              <select
                value={board.scaleId}
                onChange={(e) => onBoard({ ...board, scaleId: e.target.value })}
              >
                {SCALES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field inline">
              <span>Nominates first</span>
              <select
                value={board.ourTeamFirst ? "us" : "them"}
                onChange={(e) => onBoard({ ...board, ourTeamFirst: e.target.value === "us" })}
              >
                <option value="us">We do</option>
                <option value="them">They do</option>
              </select>
            </label>

            {/*
              App-wide rather than per-board, and deliberately mirrored from the
              phone: the same preference has to be reachable on both layouts or
              a value set on one silently governs the other.
            */}
            <label className="field inline">
              <span>Worst-matchup price</span>
              <select
                value={dodgeMode}
                onChange={(e) => onDodgeMode(e.target.value as DodgeMode)}
              >
                {DODGE_MODES.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="hint">{scale.hint}</p>
          {opening && opening.gain >= 0.005 && opening.weOpen !== board.ourTeamFirst && (
            <button
              className="ghost wide"
              onClick={() => onBoard({ ...board, ourTeamFirst: opening.weOpen })}
            >
              Win the dice-off and {opening.weOpen ? "go first" : "make them go first"} -- worth{" "}
              {opening.gain.toFixed(2)}. Click to set.
            </button>
          )}
          <button className="primary wide" onClick={onStartRound}>
            {live ? "Restart the round" : "Start the round"}
          </button>
        </section>

        <Rosters board={board} onChange={onBoard} />
      </div>
    </div>
  );
}
