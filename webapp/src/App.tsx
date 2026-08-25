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
  saveBoard,
  type Board,
} from "./model/board";
import { SCALES } from "./model/scale";
import { newRound, type LiveState } from "./engine/live";
import "./styles.css";

type Tab = "board" | "round" | "boards";

export default function App() {
  const [board, setBoard] = useState<Board>(() => loadBoards()[0] ?? emptyBoard());
  const [boards, setBoards] = useState<Board[]>(() => loadBoards());
  const [tab, setTab] = useState<Tab>("board");
  const [live, setLive] = useState<LiveState | null>(null);
  const [highlight, setHighlight] = useState<Set<string>>(new Set());

  // Persist on every edit. There is no save button, because forgetting to press
  // one between rounds is not a failure mode worth having at an event.
  useEffect(() => {
    if (board.opponent || isRated(board)) setBoards(saveBoard(board));
  }, [board]);

  const scale = boardScale(board);
  const rated = isRated(board);

  const lockedCells = useMemo(() => {
    const s = new Set<string>();
    live?.committed.forEach((c) => s.add(`${c.ours}-${c.theirs}`));
    return s;
  }, [live]);

  function startRound() {
    setLive(newRound(board.ourPlayers.length, board.ourTeamFirst));
    setTab("round");
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
              <Verdict board={board} onHighlight={setHighlight} />
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

              <button className="primary wide" onClick={startRound}>
                Start the round
              </button>
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
          <div className="boards">
            <button
              className="primary wide"
              onClick={() => {
                const b = emptyBoard(board.scaleId);
                setBoard(b);
                setLive(null);
                setTab("board");
              }}
            >
              New board
            </button>
            <ul>
              {boards.map((b) => (
                <li key={b.id}>
                  <button
                    className="board-open"
                    onClick={() => {
                      setBoard(b);
                      setLive(null);
                      setTab("board");
                    }}
                  >
                    <span>{b.opponent || "Untitled"}</span>
                    <small>{new Date(b.updatedAt).toLocaleDateString()}</small>
                  </button>
                  <button
                    className="ghost"
                    onClick={() => setBoards(deleteBoard(b.id))}
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
        )}
      </main>
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

