import { useRef, useState, type ReactNode } from "react";
import type { Board, OpponentDetail } from "../model/board";
import { boardScale, setRating, TEAM_SIZE } from "../model/board";
import { fromFraction, ratingColor, scaleValues, toFraction } from "../model/scale";

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
  /**
   * The body of the per-cell info popup, opened by a long-press on that cell.
   *
   * This is the phone's answer to the desktop overlay dropdown: the desktop can
   * paint every cell's exposure and dodge price at once because it has the room,
   * a phone cannot, so instead a hold on one cell opens a sheet with the same
   * figures for just that matchup. Only the phone Board tab supplies this;
   * omitted, cells have no hold gesture and behave exactly as before.
   *
   * Invoked lazily -- only for the cell actually held, and only while its sheet
   * is open -- so the expensive dodge solve never runs during rating entry.
   */
  cellInfo?: (ours: number, theirs: number) => ReactNode;
}

/**
 * The matchup sheet.
 *
 * Deliberately the same shape as the paper grid every team already fills in,
 * because at an event nobody wants to learn a new mental model. Tapping a cell
 * opens the value picker rather than a keyboard: phone keyboards cover half the
 * screen and typing a number is slower than hitting one of five big targets.
 */
export function Grid({ board, onChange, locked, highlight, overlay, cellInfo }: Props) {
  const scale = boardScale(board);
  const [editing, setEditing] = useState<{ ours: number; theirs: number } | null>(null);
  // Which opponent's roster popup is open, as an index into `theirPlayers`.
  // Opened by a long-press (or keyboard) on that name, and only offered for
  // players an import gave detail for -- see `OppName`.
  const [info, setInfo] = useState<number | null>(null);
  // Which cell's info popup is open. Opened by a long-press on the cell, and
  // only when `cellInfo` is supplied (the phone Board tab). See the cell button.
  const [cellHeldSel, setCellHeldSel] = useState<{ ours: number; theirs: number } | null>(null);
  const values = scaleValues(scale);

  // A long-press on a cell has to open the info sheet WITHOUT the tap-to-edit
  // firing after the finger lifts. One press happens at a time, so a pair of
  // component-level refs is enough: `cellTimer` is the pending hold, `cellHeld`
  // records that a hold fired so the click it precedes can be swallowed once.
  const cellTimer = useRef<number | null>(null);
  const cellHeld = useRef(false);
  const clearCellTimer = () => {
    if (cellTimer.current !== null) {
      window.clearTimeout(cellTimer.current);
      cellTimer.current = null;
    }
  };

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
            <th className="corner" aria-label="Our players down, theirs across" />
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
                      onClick={() => {
                        // Swallow the click that follows a long-press so a hold
                        // opens the info sheet without also opening the editor.
                        if (cellHeld.current) {
                          cellHeld.current = false;
                          return;
                        }
                        setEditing({ ours: i, theirs: j });
                      }}
                      {...(cellInfo
                        ? {
                            onPointerDown: (e: React.PointerEvent) => {
                              if (e.button !== 0) return;
                              cellHeld.current = false;
                              clearCellTimer();
                              cellTimer.current = window.setTimeout(() => {
                                cellTimer.current = null;
                                cellHeld.current = true;
                                setCellHeldSel({ ours: i, theirs: j });
                              }, 450);
                            },
                            onPointerUp: clearCellTimer,
                            onPointerLeave: clearCellTimer,
                            onPointerCancel: clearCellTimer,
                            onContextMenu: (e: React.MouseEvent) => e.preventDefault(),
                          }
                        : {})}
                      aria-label={`${board.ourPlayers[i]} versus ${board.theirPlayers[j]}`}
                    >
                      {fromFraction(f, scale)}
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
              Each cell shows the rating you picked, on this board's scale.
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

      {/*
        The per-cell overlay figures, shown on a long-press of a cell. This is
        the phone's stand-in for the desktop overlay dropdown: everything the
        desktop can paint across the whole grid -- what the opening costs, what
        refusing the matchup costs -- for the one cell the captain is holding.
        `cellInfo` is invoked here and only here, so the dodge solve it runs
        happens once, when the sheet opens, and never during rating entry.
      */}
      {cellHeldSel && cellInfo && (
        <div className="sheet-backdrop" onClick={() => setCellHeldSel(null)} role="presentation">
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <p className="sheet-title">
              {board.ourPlayers[cellHeldSel.ours]}
              <span className="vs"> vs </span>
              {board.theirPlayers[cellHeldSel.theirs]}
            </p>
            {cellInfo(cellHeldSel.ours, cellHeldSel.theirs)}
            <button type="button" className="ghost wide" onClick={() => setCellHeldSel(null)}>
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
