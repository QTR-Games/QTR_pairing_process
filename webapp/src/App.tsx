import { useEffect, useMemo, useState } from "react";
import { BoardTab } from "./components/BoardTab";
import { LivePanel } from "./components/LivePanel";
import { HomeMenu } from "./components/HomeMenu";
import { AboutHelp } from "./components/AboutHelp";
import { Splash } from "./components/Splash";
import {
  deleteBoard,
  emptyBoard,
  isRated,
  loadBoards,
  loadLive,
  saveBoard,
  saveLive,
  type Board,
} from "./model/board";
import {
  loadSettings,
  saveSettings,
  type DodgeMode,
  type AdviceLevel,
  type Settings,
  type SurpriseMode,
  type TableTracking,
  type Unit,
} from "./model/settings";
import { newRound, type LiveState } from "./engine/live";
import { DesktopWorkspace } from "./components/desktop/DesktopWorkspace";
import { useWideViewport } from "./components/desktop/useWideViewport";
import { BOARDS_RESTORED_EVENT } from "./desktop/platform";
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
 * About & Help sits off the menu and returns to it, the same shallow way the
 * app screen does.
 */
type Screen = "splash" | "home" | "about" | "app";

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
  const [roundUnit, setRoundUnit] = useState<Unit>(() => loadSettings().roundUnit);
  const [tableTracking, setTableTracking] = useState<TableTracking>(
    () => loadSettings().tableTracking,
  );
  const [screen, setScreen] = useState<Screen>("splash");

  // Set and persist in one call. Both layouts expose these preferences, so the
  // write has to live in one place or one of them will change a setting without
  // saving it. Every toggle shares one storage record with the others and with
  // the per-card currency choices, so the save is a read-modify-write against
  // what is on disk: a writer that listed the fields it knew about would drop
  // any it did not, which is exactly what happens when a new toggle is added
  // and one of the copies is missed. The card units are read fresh rather than
  // mirrored into App state because VerdictCards is their only writer.
  const persist = (patch: Partial<Settings>) =>
    saveSettings({ ...loadSettings(), ...patch });

  const changeDodgeMode = (next: DodgeMode) => {
    setDodgeMode(next);
    persist({ dodgeMode: next });
  };

  const changeAdviceLevel = (next: AdviceLevel) => {
    setAdviceLevel(next);
    persist({ adviceLevel: next });
  };

  const changeSurpriseMode = (next: SurpriseMode) => {
    setSurpriseMode(next);
    persist({ surpriseMode: next });
  };

  const changeRoundUnit = (next: Unit) => {
    setRoundUnit(next);
    persist({ roundUnit: next });
  };

  const changeTableTracking = (next: TableTracking) => {
    setTableTracking(next);
    persist({ tableTracking: next });
  };

  const changeSurpriseRegretThreshold = (next: number) => {
    const clamped = Number.isFinite(next) && next >= 0 ? next : 0;
    setSurpriseRegretThreshold(clamped);
    persist({ surpriseRegretThreshold: clamped });
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

  // A restore driven from the native menu has no React callback to reach -- the
  // menu lives in Rust, not in the backup screen. The desktop bootstrap runs the
  // restore and announces the new boards on this window event; picking them up
  // here re-renders the app without a reload. Inert on the web, where the event
  // is never fired.
  useEffect(() => {
    const onRestored = (e: Event) => {
      const boards = (e as CustomEvent<Board[]>).detail;
      if (Array.isArray(boards)) setBoards(boards);
    };
    window.addEventListener(BOARDS_RESTORED_EVENT, onRestored);
    return () => window.removeEventListener(BOARDS_RESTORED_EVENT, onRestored);
  }, []);

  // The phone Board tab pins the grid with position: sticky, and it needs to
  // sit just below the fixed header. The header height is not a constant -- a
  // long opponent name wraps to a second line -- so measure it into a CSS var
  // rather than hard-coding a top offset that would tuck the grid under a tall
  // header or leave a gap under a short one. Writing a CSS var (not React state)
  // keeps this out of the render path.
  useEffect(() => {
    const setHeadH = () => {
      const head = document.querySelector(".app-head");
      if (head instanceof HTMLElement) {
        document.documentElement.style.setProperty("--head-h", `${head.offsetHeight}px`);
      }
    };
    setHeadH();
    window.addEventListener("resize", setHeadH);
    return () => window.removeEventListener("resize", setHeadH);
  }, [screen, wide]);

  const lockedCells = useMemo(() => {
    const s = new Set<string>();
    live?.committed.forEach((c) => s.add(`${c.ours}-${c.theirs}`));
    return s;
  }, [live]);

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
          roundUnit={roundUnit}
          onRoundUnit={changeRoundUnit}
          tableTracking={tableTracking}
          onTableTracking={changeTableTracking}
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
          onHelp={() => setScreen("about")}
          onRestored={setBoards}
        />
      </div>
    );
  }

  if (screen === "about") {
    return (
      <div className="app app-launch">
        <AboutHelp onBack={() => setScreen("home")} />
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
              roundUnit={roundUnit}
              onRoundUnit={changeRoundUnit}
              tableTracking={tableTracking}
              onTableTracking={changeTableTracking}
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
          <BoardTab
            board={board}
            onBoardChange={setBoard}
            highlight={highlight}
            onHighlight={setHighlight}
            lockedCells={lockedCells}
            dodgeMode={dodgeMode}
            onStartRound={startRound}
          />
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
              roundUnit={roundUnit}
              tableTracking={tableTracking}
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
 * This used to lead with `./klikklak.apk`, a relative link to an installer
 * published alongside the Pages site. The site is back, but the APK is not: an
 * installer on a public URL is downloadable by anyone, and Pages has no access
 * control below Enterprise Cloud. Android installs come off a laptop instead,
 * with `npm run phone:install` (scripts/Install-ToPhone.ps1) -- which is
 * deliberately not something the person reading this page can do themselves.
 *
 * The iOS half is the reason the site exists at all: there is no sideloading, so
 * "Add to Home Screen" from this page is the only route onto an iPhone, and it
 * yields the same offline-capable bundle the APK wraps.
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
