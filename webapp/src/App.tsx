import { useEffect, useMemo, useState } from "react";
import { Grid, Rosters } from "./components/Grid";
import { LivePanel } from "./components/LivePanel";
import { Verdict } from "./components/Verdict";
import {
  boardScale,
  deleteBoard,
  emptyBoard,
  isRated,
  loadBoards,
  loadLive,
  saveBoard,
  saveLive,
  type Board,
} from "./model/board";
import { SCALES } from "./model/scale";
import { DODGE_MODES, loadSettings, saveSettings, type DodgeMode } from "./model/settings";
import { newRound, type LiveState } from "./engine/live";
import { boardMatrix } from "./model/board";
import { openingChoice } from "./engine/protocol";
import { DesktopWorkspace } from "./components/desktop/DesktopWorkspace";
import { useWideViewport } from "./components/desktop/useWideViewport";
import "./styles.css";

type Tab = "board" | "round" | "boards";

export default function App() {
  const [board, setBoard] = useState<Board>(() => loadBoards()[0] ?? emptyBoard());
  const [boards, setBoards] = useState<Board[]>(() => loadBoards());
  const [tab, setTab] = useState<Tab>(() => {
    // Land on the round if one is already in progress. Opening to the board
    // after a reload looks exactly like having lost it.
    const first = loadBoards()[0];
    return first && loadLive(first.id) ? "round" : "board";
  });
  const [live, setLive] = useState<LiveState | null>(() => {
    // Resume whatever was in progress. Reached after a reload, after Android
    // reclaimed the app, or after a new build took over -- none of which should
    // cost you a round you are standing in the middle of.
    const first = loadBoards()[0];
    return first ? loadLive(first.id) : null;
  });
  const [highlight, setHighlight] = useState<Set<string>>(new Set());
  const [dodgeMode, setDodgeMode] = useState<DodgeMode>(() => loadSettings().dodgeMode);

  /**
   * Which of the two layouts to render.
   *
   * A branch rather than a reflow. The phone tree below is exactly what it was
   * before the desktop workspace existed, and it is what a 390px viewport gets;
   * the workspace is a separate component that a phone never mounts. That is
   * deliberate insurance -- the phone build ships to an event, and a shared
   * layout that merely restyles itself is one careless selector away from a
   * regression nobody notices until the venue.
   */
  const wide = useWideViewport();

  // Persist on every edit. There is no save button, because forgetting to press
  // one between rounds is not a failure mode worth having at an event.
  useEffect(() => {
    if (board.opponent || isRated(board)) setBoards(saveBoard(board));
  }, [board]);

  // Same rule for the round itself.
  useEffect(() => {
    saveLive(board.id, live);
  }, [board.id, live]);

  const scale = boardScale(board);
  const rated = isRated(board);

  const lockedCells = useMemo(() => {
    const s = new Set<string>();
    live?.committed.forEach((c) => s.add(`${c.ours}-${c.theirs}`));
    return s;
  }, [live]);

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

  function startRound() {
    setLive(newRound(board.ourPlayers.length, board.ourTeamFirst));
    setTab("round");
  }

  if (wide) {
    return (
      <div className="app app-wide">
        <header className="app-head">
          <h1>{board.opponent || "New board"}</h1>
          <nav className="tabs">
            {/*
              Two tabs, not three. Board and Round are the same screen here,
              which is the whole reason to have a bigger one.
            */}
            <button className={tab !== "boards" ? "on" : ""} onClick={() => setTab("board")}>
              Workspace
            </button>
            <button className={tab === "boards" ? "on" : ""} onClick={() => setTab("boards")}>
              Saved
            </button>
          </nav>
        </header>
        <main>
          {tab === "boards" ? (
            <BoardsPanel
              boards={boards}
              scaleId={board.scaleId}
              onNew={(b) => {
                setBoard(b);
                setLive(null);
                setTab("board");
              }}
              onOpen={(b) => {
                setBoard(b);
                const resumed = loadLive(b.id);
                setLive(resumed);
                setTab("board");
              }}
              onDelete={(id) => setBoards(deleteBoard(id))}
            />
          ) : (
            <DesktopWorkspace
              board={board}
              onBoard={setBoard}
              live={live}
              onLive={setLive}
              onStartRound={startRound}
            />
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-head">
        <h1>{board.opponent || "New board"}</h1>
        <nav className="tabs">
          <button className={tab === "board" ? "on" : ""} onClick={() => setTab("board")}>
            Board
          </button>
          <button className={tab === "round" ? "on" : ""} onClick={() => setTab("round")}>
            Round
          </button>
          <button className={tab === "boards" ? "on" : ""} onClick={() => setTab("boards")}>
            Saved
          </button>
        </nav>
      </header>

      <main>
        {tab === "board" && (
          <>
            {/*
              Setup and reading want opposite orders. On a fresh board you are
              typing names, so the rosters belong at the top; once anything is
              rated you are reading the position, so the verdict does. Keying
              this off isRated means the screen reorders itself as the board
              fills in, with nothing to toggle at an event.
            */}
            {rated ? (
              <Verdict board={board} onHighlight={setHighlight} dodgeMode={dodgeMode} />
            ) : (
              <Rosters board={board} onChange={setBoard} />
            )}
            <Grid board={board} onChange={setBoard} highlight={highlight} locked={lockedCells} />
            <div className="controls">
              <label className="field inline">
                <span>Scale</span>
                <select
                  value={board.scaleId}
                  onChange={(e) => setBoard({ ...board, scaleId: e.target.value })}
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
                  onChange={(e) => setBoard({ ...board, ourTeamFirst: e.target.value === "us" })}
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
                    onClick={() => setBoard({ ...board, ourTeamFirst: opening.weOpen })}
                  >
                    Win the dice-off and{" "}
                    {opening.weOpen ? "go first" : "make them go first"} -- worth{" "}
                    {opening.gain.toFixed(2)}. Tap to set.
                  </button>
                )
              )}

              <button className="primary wide" onClick={startRound}>
                Start the round
              </button>

              {/*
                App-wide, not per-board: a preference about how much the screen
                says, which should survive moving between boards.
              */}
              <label className="field inline">
                <span>Show the worst-matchup price</span>
                <select
                  value={dodgeMode}
                  onChange={(e) => {
                    const next = e.target.value as DodgeMode;
                    setDodgeMode(next);
                    saveSettings({ dodgeMode: next });
                  }}
                >
                  {DODGE_MODES.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {/* Whichever of the two did not lead goes here, so neither is lost. */}
            {rated && <Rosters board={board} onChange={setBoard} />}
          </>
        )}

        {tab === "round" &&
          (live ? (
            <LivePanel
              board={board}
              state={live}
              onState={setLive}
              onReset={() => setLive(newRound(board.ourPlayers.length, board.ourTeamFirst))}
            />
          ) : (
            <div className="empty">
              <p>No round in progress.</p>
              <button className="primary" onClick={startRound}>
                Start the round
              </button>
            </div>
          ))}

        {tab === "boards" && (
          <BoardsPanel
            boards={boards}
            scaleId={board.scaleId}
            onNew={(b) => {
              setBoard(b);
              setLive(null);
              setTab("board");
            }}
            onOpen={(b) => {
              setBoard(b);
              // Resume that board's round if it has one, rather than
              // silently discarding it just because you looked away.
              const resumed = loadLive(b.id);
              setLive(resumed);
              setTab(resumed ? "round" : "board");
            }}
            onDelete={(id) => setBoards(deleteBoard(id))}
          />
        )}
      </main>
    </div>
  );
}

interface BoardsPanelProps {
  boards: Board[];
  scaleId: string;
  onNew: (b: Board) => void;
  onOpen: (b: Board) => void;
  onDelete: (id: string) => void;
}

/**
 * The saved-board list.
 *
 * Lifted out of the tab body unchanged so both layouts render the same markup.
 * The only difference between them is where the caller sends you afterwards:
 * the phone jumps to the round when one is in progress, because it cannot show
 * you the board and the round at the same time. The desktop workspace can, so
 * it always lands on the workspace.
 */
function BoardsPanel({ boards, scaleId, onNew, onOpen, onDelete }: BoardsPanelProps) {
  return (
    <div className="boards">
      <button className="primary wide" onClick={() => onNew(emptyBoard(scaleId))}>
        New board
      </button>
      <ul>
        {boards.map((b) => (
          <li key={b.id}>
            <button className="board-open" onClick={() => onOpen(b)}>
              <span>{b.opponent || "Untitled"}</span>
              <small>{new Date(b.updatedAt).toLocaleDateString()}</small>
            </button>
            <button
              className="ghost"
              onClick={() => onDelete(b.id)}
              aria-label={`Delete ${b.opponent}`}
            >
              Delete
            </button>
          </li>
        ))}
        {boards.length === 0 && <p className="hint">Nothing saved yet.</p>}
      </ul>
      <InstallNote />
    </div>
  );
}

/*
 * How a teammate gets this onto their own phone.
 *
 * Two ways in, because Android and iOS disagree about what an app is. Android
 * takes the APK, which behaves like anything else installed on the device. iOS
 * has no sideloading, so it gets the home-screen route -- which is the same
 * bundle, offline-capable once opened, just launched differently.
 *
 * It hides once the app is installed. Someone reading this inside the installed
 * app has already done the thing it is asking them to do.
 */
function InstallNote() {
  const installed =
    "Capacitor" in window ||
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS predates the display-mode media query and reports it this way.
    (navigator as unknown as { standalone?: boolean }).standalone === true;

  if (installed) return null;

  return (
    <section className="install-note">
      <h2>Put this on a phone</h2>
      <p>
        <a href="./qtr-pairing.apk">Download the Android app</a> — open the file
        and allow the install when the phone asks.
      </p>
      <p className="hint">
        On iPhone there is no download. Use Share, then “Add to Home Screen”.
        Either way it works with no signal after the first open.
      </p>
    </section>
  );
}

