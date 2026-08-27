import { useRef, useState, type ReactNode } from "react";
import type { Board, OpponentDetail } from "../model/board";
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
  // Which opponent's roster popup is open, as an index into `theirPlayers`.
  // Opened by a long-press (or keyboard) on that name, and only offered for
  // players an import gave detail for -- see `OppName`.
  const [info, setInfo] = useState<number | null>(null);
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
                <OppName name={name} detail={board.theirDetails?.[j]} onOpen={() => setInfo(j)} />
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

      {/*
        The opponent's roster, shown on a long-press of their name. Reference
        material for the captain at pairing time -- who is across the table, what
        they registered -- and nothing the engine reads. Only reachable for names
        an import carried detail for; a hand-entered board never opens this.
      */}
      {info != null && (
        <div className="sheet-backdrop" onClick={() => setInfo(null)} role="presentation">
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <p className="sheet-title">{board.theirPlayers[info]}</p>
            <OpponentDetailView detail={board.theirDetails?.[info]} />
            <button type="button" className="ghost wide" onClick={() => setInfo(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Press-and-hold, as a set of handlers to spread onto an element.
 *
 * A long-press rather than a tap because the opponent's name sits on the grid
 * header the captain is reading past constantly; a tap-to-open would fire by
 * accident every time a thumb brushed it. The keyboard has no "hold", so
 * Enter/Space opens immediately -- the accessible equivalent of the gesture.
 */
function useLongPress(onLongPress: () => void, ms = 450) {
  const timer = useRef<number | null>(null);
  const clear = () => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  };
  return {
    onPointerDown: (e: React.PointerEvent) => {
      // Ignore anything but the primary button; a right-click is the context
      // menu, not a hold.
      if (e.button !== 0) return;
      clear();
      timer.current = window.setTimeout(() => {
        timer.current = null;
        onLongPress();
      }, ms);
    },
    onPointerUp: clear,
    onPointerLeave: clear,
    onPointerCancel: clear,
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onLongPress();
      }
    },
  };
}

/**
 * One opponent's name in the grid header.
 *
 * Plain text when the board carries no roster detail for that player -- which is
 * every hand-entered board -- so the header is byte-identical to what it was.
 * When an import did carry detail, the name becomes a hold target that opens the
 * roster popup.
 */
function OppName({
  name,
  detail,
  onOpen,
}: {
  name: string;
  detail?: OpponentDetail;
  onOpen: () => void;
}) {
  const press = useLongPress(onOpen);
  const hasInfo = !!(detail && (detail.faction || detail.lists?.length));
  if (!hasInfo) return <span>{name}</span>;
  return (
    <button
      type="button"
      className="opp-name"
      title={`${name} -- hold for roster`}
      aria-label={`${name}. Hold for roster.`}
      onContextMenu={(e) => e.preventDefault()}
      {...press}
    >
      <span>{name}</span>
    </button>
  );
}

/** The roster popup body: the faction and the lists an opponent registered. */
function OpponentDetailView({ detail }: { detail?: OpponentDetail }) {
  const lists = detail?.lists ?? [];
  return (
    <div className="opp-detail">
      {detail?.faction ? <p className="opp-faction">{detail.faction}</p> : null}
      {lists.length > 0 ? (
        <ul className="opp-lists">
          {lists.map((l, k) => {
            const label = [l.leader, l.army].filter(Boolean).join(" -- ");
            return <li key={k}>{label || `List ${k + 1}`}</li>;
          })}
        </ul>
      ) : (
        <p className="sheet-hint">No lists recorded for this player.</p>
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
