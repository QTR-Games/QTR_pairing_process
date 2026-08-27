import { useMemo, useState } from "react";
import { dodgeMapChance } from "../../engine/avoidance";
import { evenThreshold } from "../../engine/boardAnalysis";
import { cellOutlooks } from "../../engine/boardAnalysis";
import type { Matrix } from "../../engine/boardAnalysis";
import type { LiveState } from "../../engine/live";
import { openingChoice } from "../../engine/protocol";
import { boardMatrix, boardScale, isRated, type Board } from "../../model/board";
import { SCALES } from "../../model/scale";

/** Which analysis, if any, is drawn inside the 25 cells. */
type OverlayMode = "none" | "exposure" | "dodge";
import {
  ADVICE_LEVELS,
  DODGE_MODES,
  type AdviceLevel,
  type DodgeMode,
} from "../../model/settings";
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
  adviceLevel: AdviceLevel;
  onAdviceLevel: (l: AdviceLevel) => void;
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
  adviceLevel,
  onAdviceLevel,
}: Props) {
  const scale = boardScale(board);
  const rated = isRated(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);

  const [highlight, setHighlight] = useState<Set<string>>(new Set());
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("none");
  const heat = overlayMode === "dodge";

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

  /**
   * Guaranteed floor and reachable ceiling for all 25 openings, and what each
   * one costs against the best available floor.
   *
   * This is the structure `decisionReport.frontier` is derived from, and it is
   * shown INSTEAD of that frontier on purpose. Measured over the 31 saved
   * boards, the frontier collapses to a single distinct (floor, ceiling) offer
   * on 30 of them -- a frontier of ten cells is ten cells holding the same
   * value, which is a tie and not a trade-off. Drawing it would be a UI for a
   * one-element set.
   *
   * The map underneath it is the opposite. The floor spread across the 25 cells
   * averages 2.61 points, runs 1.00 to 4.00, and is never flat on any board.
   * About 22 of the 25 cells cost a full point or more against the best cell,
   * and only about 3 tie it -- on 12 of 31 boards exactly one cell does. So the
   * honest reading is not "here are your good options", it is "most of this
   * board is a mistake, and here are the two or three that are not".
   *
   * Costs 0.18 ms mean and 0.50 ms worst, so unlike the dodge map this is safe
   * to leave running; it is behind the selector only because the two overlays
   * compete for the same cell slot.
   */
  const exposureMap = useMemo(() => {
    if (overlayMode !== "exposure" || !rated) return null;
    const outlooks = cellOutlooks(matrix, tau);
    let bestFloor = -Infinity;
    for (const o of outlooks.values()) bestFloor = Math.max(bestFloor, o.floor);
    let worstCost = 0;
    for (const o of outlooks.values()) worstCost = Math.max(worstCost, bestFloor - o.floor);
    return { outlooks, bestFloor, worstCost };
  }, [overlayMode, rated, matrix, tau]);

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
    : exposureMap
      ? (i: number, j: number) => {
          const o = exposureMap.outlooks.get(`${i},${j}`);
          if (!o) return null;
          const cost = exposureMap.bestFloor - o.floor;
          if (cost < 1e-9) {
            return (
              <span className="heat best">
                <span className="heat-num">{o.floor.toFixed(1)} best</span>
              </span>
            );
          }
          const share = exposureMap.worstCost > 0 ? cost / exposureMap.worstCost : 0;
          return (
            <span className="heat cost">
              <span className="heat-bar" style={{ width: `${Math.round(share * 100)}%` }} />
              <span className="heat-num">
                {o.floor.toFixed(1)} &minus;{cost.toFixed(1)}
              </span>
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
              <span>Overlay</span>
              <select
                value={overlayMode}
                onChange={(e) => setOverlayMode(e.target.value as OverlayMode)}
              >
                <option value="none">None</option>
                <option value="exposure">What each opening costs</option>
                <option value="dodge">Price every dodge</option>
              </select>
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
          {overlayMode === "exposure" && (
            <p className="hint">
              Each cell shows the round total you are still <em>guaranteed</em> if
              that matchup happens, and what it gives up against the best opening
              available. <strong>best</strong> marks the cells nothing beats.
              Across the 31 saved event boards about 22 of the 25 cells cost a
              full point or more and only about 3 tie the best, so read this as a
              map of what to avoid rather than a menu. Costs 0.18 ms.
            </p>
          )}
          {overlayMode === "none" && (
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
            <LivePanel
              board={board}
              state={live}
              onState={onLive}
              adviceLevel={adviceLevel}
              onReset={onStartRound}
            />
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
                // Resolved id, not the stored one. Everything else on screen goes
                // through scaleById, which falls back to 1-5 for an id it does not
                // recognise -- so a board carrying a legacy or hand-edited scaleId
                // renders a 1-5 grid while this select, matching no option, silently
                // displays the first one instead. That reads as "Stoplight", a 1-3
                // scale, over a grid full of 4s and 5s. Binding to the same resolver
                // the grid uses makes the two incapable of disagreeing.
                value={boardScale(board).id}
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

            {/* Same preference, same mirror requirement as the dodge price. */}
            <label className="field inline">
              <span>Round advice</span>
              <select
                value={adviceLevel}
                onChange={(e) => onAdviceLevel(e.target.value as AdviceLevel)}
              >
                {ADVICE_LEVELS.map((m) => (
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
