import { useEffect, useMemo, useState } from "react";
import { Grid, Rosters } from "./components/Grid";
import { LivePanel } from "./components/LivePanel";
import { Verdict } from "./components/Verdict";
import { HomeMenu } from "./components/HomeMenu";
import { Splash } from "./components/Splash";
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
import {
  loadSettings,
  saveSettings,
  type DodgeMode,
  type AdviceLevel,
  type SurpriseMode,
} from "./model/settings";
import { newRound, type LiveState } from "./engine/live";
import { boardMatrix } from "./model/board";
import { openingChoice } from "./engine/protocol";
import { DesktopWorkspace } from "./components/desktop/DesktopWorkspace";
import { useWideViewport } from "./components/desktop/useWideViewport";
import "./styles.css";

type Tab = "board" | "round" | "boards";

/**
 * Which of the three screens is up.
 *
 * A flat state rather than a route. The app is one bundle with no URL to speak
 * of -- it runs from a file:// origin inside a WebView -- so a router would buy
 * nothing and cost a back-button contract nobody has written down.
 *
 * The order is fixed: splash, then menu, then the app. Only the last of the
 * three is reachable in both directions, via the Menu button in the header.
 */
type Screen = "splash" | "home" | "app";

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
  const [adviceLevel, setAdviceLevel] = useState<AdviceLevel>(
    () => loadSettings().adviceLevel,
  );
  const [surpriseMode, setSurpriseMode] = useState<SurpriseMode>(() => loadSettings().surpriseMode);
  const [surpriseRegretThreshold, setSurpriseRegretThreshold] = useState<number>(
    () => loadSettings().surpriseRegretThreshold,
  );
  const [screen, setScreen] = useState<Screen>("splash");

  // Set and persist in one call. Both layouts expose this preference, so the
  // write has to live in one place or one of them will change it without
  // saving it. Both toggles share one storage record, so each writer has to
  // hand the other's current value back or a save would wipe it.
  const changeDodgeMode = (next: DodgeMode) => {
    setDodgeMode(next);
    saveSettings({ dodgeMode: next, adviceLevel, surpriseMode, surpriseRegretThreshold });
  };

  const changeAdviceLevel = (next: AdviceLevel) => {
    setAdviceLevel(next);
    saveSettings({ dodgeMode, adviceLevel: next, surpriseMode, surpriseRegretThreshold });
  };

  const changeSurpriseMode = (next: SurpriseMode) => {
    setSurpriseMode(next);
    saveSettings({ dodgeMode, adviceLevel, surpriseMode: next, surpriseRegretThreshold });
  };

  const changeSurpriseRegretThreshold = (next: number) => {
    const clamped = Number.isFinite(next) && next >= 0 ? next : 0;
    setSurpriseRegretThreshold(clamped);
    saveSettings({ dodgeMode, adviceLevel, surpriseMode, surpriseRegretThreshold: clamped });
  };

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

  /**
   * Leave the menu for the app, landing on a given tab.
   *
   * One helper rather than a closure per menu item, so every route out of the
   * menu makes the same two writes and a fourth item cannot be added later
   * that changes the tab but forgets the screen.
   */
  const enter = (to: Tab) => {
    setTab(to);
    setScreen("app");
  };

  /*
    The launch screen, rendered alone.

    It would look better layered over the menu, fading to reveal it. It is not,
    and the reason is worth writing down: under `prefers-reduced-motion` the
    splash calls `onDone` synchronously from its own `pointerdown` handler.
    React flushes discrete events synchronously, so the splash would unmount
    between `pointerdown` and `pointerup`, and the tap that dismissed it would
    land as a `click` on whatever had been underneath -- which is the menu's
    primary button. Nothing beneath it means nothing to hit by accident.

    Everything above this line is a hook, so both early returns below are safe.
  */
  if (screen === "splash") {
    return (
      <div className="app app-launch">
        <Splash onDone={() => setScreen("home")} />
      </div>
    );
  }

  if (screen === "home") {
    return (
      <div className="app app-launch">
        <HomeMenu
          /*
            `Untitled` rather than null, matching what the saved list already
            calls an unnamed board. Passing null would hide the resume button
            for exactly the person who most needs it: someone mid-round who
            never stopped to type the opponent's name.
          */
          liveOpponent={live ? board.opponent.trim() || "Untitled" : null}
          lastBoard={boards[0] ?? null}
          boardCount={boards.length}
          dodgeMode={dodgeMode}
          onDodgeMode={changeDodgeMode}
          adviceLevel={adviceLevel}
          onAdviceLevel={changeAdviceLevel}
          surpriseMode={surpriseMode}
          onSurpriseMode={changeSurpriseMode}
          surpriseRegretThreshold={surpriseRegretThreshold}
          onSurpriseRegretThreshold={changeSurpriseRegretThreshold}
          onResume={() => enter("round")}
          onContinue={() => {
            /*
              Open the board the button actually names. These are normally the
              same object -- the loaded board is the most recent one -- but a
              delete from the saved list can leave them apart, and a button
              that opens something other than what it says is worse than no
              button.
            */
            const last = boards[0];
            if (last && last.id !== board.id) {
              setBoard(last);
              setLive(loadLive(last.id));
            }
            enter("board");
          }}
          onBoards={() => enter("boards")}
          onRestored={setBoards}
        />
      </div>
    );
  }

  if (wide) {
    return (
      <div className="app app-wide">
        <header className="app-head">
          <div className="app-title">
            <button className="ghost app-menu" onClick={() => setScreen("home")}>
              Menu
            </button>
            <h1>{board.opponent || "New board"}</h1>
          </div>
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
              dodgeMode={dodgeMode}
              onDodgeMode={changeDodgeMode}
              adviceLevel={adviceLevel}
              onAdviceLevel={changeAdviceLevel}
              surpriseMode={surpriseMode}
              onSurpriseMode={changeSurpriseMode}
              surpriseRegretThreshold={surpriseRegretThreshold}
              onSurpriseRegretThreshold={changeSurpriseRegretThreshold}
            />
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-head">
        <div className="app-title">
          <button className="ghost app-menu" onClick={() => setScreen("home")}>
            Menu
          </button>
          <h1>{board.opponent || "New board"}</h1>
        </div>
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
                  // Resolved id, not the stored one -- see the matching note in
                  // DesktopWorkspace. An unrecognised scaleId falls back to 1-5
                  // everywhere except here, where it would show "Stoplight".
                  value={scale.id}
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
              adviceLevel={adviceLevel}
              surpriseMode={surpriseMode}
              surpriseRegretThreshold={surpriseRegretThreshold}
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
 *
 * Backup and restore used to sit at the bottom of this list and now lives in
 * the menu instead. One copy, not two: it is a three-way export/import with a
 * file picker, a clipboard path and a textarea, and two of those rendered on
 * two screens is twice the surface to get wrong on the morning someone is
 * actually restoring a season of boards.
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
      <p className="hint">Backing up and restoring boards is in Menu &rarr; Back up and restore.</p>
      <InstallNote />
    </div>
  );
}

/*
 * How a teammate gets this onto their own phone.
 *
 * This used to lead with `./klikklak.apk`, a relative link that only ever
 * resolved on the GitHub Pages site. Pages cannot serve a private repository on
 * the Free plan, the site is gone, and it is not coming back -- so that link
 * pointed at a file that can no longer exist anywhere. It is removed rather
 * than repointed: Android installs now come off a laptop with
 * `npm run phone:install` (scripts/Install-ToPhone.ps1), which is a thing the
 * person holding the phone cannot do from the page they are reading.
 *
 * The iOS half survives, because it is still true and still the only iOS route
 * -- there is no sideloading, so "Add to Home Screen" from whatever URL this
 * page was opened from is how an iPhone gets it, and the result is the same
 * offline-capable bundle.
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
        On iPhone, use Share, then “Add to Home Screen”. It works with no signal
        after the first open.
      </p>
      <p className="hint">
        On Android, ask whoever is running the laptop to install it —{" "}
        <code>npm run phone:install</code> puts the app on a paired phone over
        Wi-Fi. There is no download link here on purpose.
      </p>
    </section>
  );
}
