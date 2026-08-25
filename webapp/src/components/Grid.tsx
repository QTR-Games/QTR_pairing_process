import { useState } from "react";
import type { Board } from "../model/board";
import { boardScale, setRating, TEAM_SIZE } from "../model/board";
import { fromFraction, ratingColor, scaleValues, toFraction } from "../model/scale";

interface Props {
  board: Board;
  onChange: (b: Board) => void;
  /** Cells already locked in by committed pairings, as "ours-theirs". */
  locked?: Set<string>;
  /** Cells to outline as the recommendation. */
  highlight?: Set<string>;
}

/**
 * The matchup sheet.
 *
 * Deliberately the same shape as the paper grid every team already fills in,
 * because at an event nobody wants to learn a new mental model. Tapping a cell
 * opens the value picker rather than a keyboard: phone keyboards cover half the
 * screen and typing a number is slower than hitting one of five big targets.
 */
export function Grid({ board, onChange, locked, highlight }: Props) {
  const scale = boardScale(board);
  const [editing, setEditing] = useState<{ ours: number; theirs: number } | null>(null);
  const values = scaleValues(scale);

  return (
    <div className="grid-wrap">
      <table className="grid">
        <thead>
          <tr>
            <th className="corner" aria-label="Our players down, theirs across" />
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
                      {fromFraction(f, scale)}
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
