import { useState, type ReactNode } from "react";
import type { Board } from "../model/board";
import { boardScale, setRating, TEAM_SIZE } from "../model/board";
import { ratingColor, scaleValues, toFraction } from "../model/scale";
import { winProbabilityFromFraction } from "../engine/winProbability";

interface Props {
  board: Board;
  onChange: (b: Board) => void;
  /** Cells already locked in by committed pairings, as "ours-theirs". */
  locked?: Set<string>;
  /** Cells to outline as the recommendation. */
  highlight?: Set<string>;
  /**
   * Extra content to render inside each cell, under the rating.
   *
   * Only ever supplied by the desktop workspace, which uses it for the dodge
   * heat map. Omitted everywhere else, and when omitted this renders nothing at
   * all -- so the phone grid is byte-identical to what it was before this prop
   * existed. Returning null for a cell is the normal case even on desktop.
   */
  overlay?: (ours: number, theirs: number) => ReactNode;
}

/**
 * The matchup sheet.
 *
 * Deliberately the same shape as the paper grid every team already fills in,
 * because at an event nobody wants to learn a new mental model. Tapping a cell
 * opens the value picker rather than a keyboard: phone keyboards cover half the
 * screen and typing a number is slower than hitting one of five big targets.
 */
export function Grid({ board, onChange, locked, highlight, overlay }: Props) {
  const scale = boardScale(board);
  const [editing, setEditing] = useState<{ ours: number; theirs: number } | null>(null);
  const values = scaleValues(scale);

  // The captain's protect-first pick, marked on that player's row so the call
  // made on the reading screen is visible while looking at the sheet. Trusted
  // raw with only a range guard: Verdict owns the invariant that this field is
  // null or a live, exposed index, and it is co-mounted wherever the grid shows.
  const marked =
    board.protectPriority != null && board.protectPriority < board.ourPlayers.length
      ? board.protectPriority
      : null;

  return (
    <div className="grid-wrap">
      <table className="grid">
        <thead>
          <tr>
            <th className="corner" aria-label="Our players down, theirs across">
              <span className="corner-unit">win %</span>
            </th>
            {board.theirPlayers.map((name, j) => (
              <th key={j} className="col-head" title={name}>
                <span>{name}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {board.ourPlayers.map((name, i) => (
            <tr key={i}>
              <th className="row-head" title={name}>
                <span>{name}</span>
                {marked === i && (
                  <span className="protect-mark" title="Protect first" aria-label="Protect first" />
                )}
              </th>
              {board.theirPlayers.map((_, j) => {
                const f = board.fractions[i][j];
                const key = `${i}-${j}`;
                const isLocked = locked?.has(key);
                const isHigh = highlight?.has(key);
                return (
                  <td key={j}>
                    <button
                      type="button"
                      className={
                        "cell" + (isLocked ? " locked" : "") + (isHigh ? " highlight" : "")
                      }
                      style={{ background: ratingColor(f) }}
                      onClick={() => setEditing({ ours: i, theirs: j })}
                      aria-label={`${board.ourPlayers[i]} versus ${board.theirPlayers[j]}`}
                    >
                      {Math.round(winProbabilityFromFraction(f) * 100)}
                      {overlay?.(i, j)}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {editing && (
        <div
          className="sheet-backdrop"
          onClick={() => setEditing(null)}
          role="presentation"
        >
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <p className="sheet-title">
              {board.ourPlayers[editing.ours]}
              <span className="vs"> vs </span>
              {board.theirPlayers[editing.theirs]}
            </p>
            <div className="value-row">
              {values.map((v) => {
                const f = toFraction(v, scale);
                const current =
                  Math.abs(board.fractions[editing.ours][editing.theirs] - f) < 1e-9;
                return (
                  <button
                    key={v}
                    type="button"
                    className={"value" + (current ? " current" : "")}
                    style={{ background: ratingColor(f) }}
                    onClick={() => {
                      onChange(setRating(board, editing.ours, editing.theirs, v, scale));
                      setEditing(null);
                    }}
                  >
                    {v}
                  </button>
                );
              })}
            </div>
            <p className="sheet-hint">
              Worst matchup on the left, best on the right. The midpoint is an even game.
              The grid reads each cell back as that player's per-game win chance.
            </p>
            <button type="button" className="ghost wide" onClick={() => setEditing(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

interface NamesProps {
  board: Board;
  onChange: (b: Board) => void;
}

/** Roster entry. Kept separate so the grid stays the focus of the board screen. */
export function Rosters({ board, onChange }: NamesProps) {
  return (
    <div className="rosters">
      <label className="field">
        <span>Opponent team</span>
        <input
          value={board.opponent}
          placeholder="e.g. Opponent 02"
          onChange={(e) => onChange({ ...board, opponent: e.target.value })}
        />
      </label>

      <div className="roster-cols">
        <div>
          <h3>Us</h3>
          {Array.from({ length: TEAM_SIZE }, (_, i) => (
            <input
              key={i}
              value={board.ourPlayers[i]}
              onChange={(e) => {
                const ourPlayers = [...board.ourPlayers];
                ourPlayers[i] = e.target.value;
                onChange({ ...board, ourPlayers });
              }}
            />
          ))}
        </div>
        <div>
          <h3>Them</h3>
          {Array.from({ length: TEAM_SIZE }, (_, i) => (
            <input
              key={i}
              value={board.theirPlayers[i]}
              onChange={(e) => {
                const theirPlayers = [...board.theirPlayers];
                theirPlayers[i] = e.target.value;
                onChange({ ...board, theirPlayers });
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
