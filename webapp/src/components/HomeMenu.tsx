/*
  The front door.

  Until now the app opened straight onto a grid, which left nowhere to put
  anything that is not a pairing decision -- settings, backups, help, a bug
  report. This is that place.

  The tension worth naming: this screen costs a tap on the way to the board, and
  the board is what someone opens the app for while a round clock runs. So the
  primary action is contextual and always first. If a round is live it offers to
  resume that round by name; otherwise it offers the most recently touched
  board by name; only with nothing saved at all does it fall back to a generic
  entry. Everything else is secondary and can afford to be a tap deeper.

  Secondary items use <details> rather than routing. There is no navigation
  stack to get lost in, back-button behaviour stays whatever the browser does,
  and the whole screen remains one scrollable thing on a phone.
*/
import { BoardBackup } from "./BoardBackup";
import { LongshanksImport } from "./LongshanksImport";
import { BRAND, LINKS } from "../brand";
import {
  ADVICE_LEVELS,
  ROUND_UNITS,
  DODGE_MODES,
  SURPRISE_MODES,
  type AdviceLevel,
  type DodgeMode,
  type SurpriseMode,
  type Unit,
} from "../model/settings";
import type { Board } from "../model/board";

interface HomeMenuProps {
  /** Name of the opponent whose round is mid-flight, if any. */
  liveOpponent: string | null;
  /** Most recently updated board, used to label the primary action. */
  lastBoard: Board | null;
  boardCount: number;
  dodgeMode: DodgeMode;
  onDodgeMode: (mode: DodgeMode) => void;
  adviceLevel: AdviceLevel;
  onAdviceLevel: (level: AdviceLevel) => void;
  surpriseMode: SurpriseMode;
  onSurpriseMode: (mode: SurpriseMode) => void;
  surpriseRegretThreshold: number;
  onSurpriseRegretThreshold: (threshold: number) => void;
  roundUnit: Unit;
  onRoundUnit: (unit: Unit) => void;
  /** Resume the live round. Only called when `liveOpponent` is set. */
  onResume: () => void;
  /** Open the most recent board on the pairing screen. */
  onContinue: () => void;
  /** Open the saved-boards list. */
  onBoards: () => void;
  /** Open the About & Help screen. */
  onHelp: () => void;
  onRestored: (boards: Board[]) => void;
}

export function HomeMenu({
  liveOpponent,
  lastBoard,
  boardCount,
  dodgeMode,
  onDodgeMode,
  adviceLevel,
  onAdviceLevel,
  surpriseMode,
  onSurpriseMode,
  surpriseRegretThreshold,
  onSurpriseRegretThreshold,
  roundUnit,
  onRoundUnit,
  onResume,
  onContinue,
  onBoards,
  onHelp,
  onRestored,
}: HomeMenuProps) {
  return (
    <div className="home" data-testid="home">
      <header className="home-head">
        <img src={BRAND.logo} alt="" width={72} height={70} draggable={false} />
        <div>
          <h1>{BRAND.product}</h1>
          <p className="home-by">by {BRAND.name}</p>
        </div>
      </header>

      {liveOpponent ? (
        <button className="primary wide home-primary" onClick={onResume}>
          Resume round vs {liveOpponent}
        </button>
      ) : lastBoard && lastBoard.opponent.trim() ? (
        <button className="primary wide home-primary" onClick={onContinue}>
          Open {lastBoard.opponent}
        </button>
      ) : (
        <button className="primary wide home-primary" onClick={onContinue}>
          Start a new board
        </button>
      )}

      <button className="ghost wide" onClick={onBoards}>
        {boardCount > 0 ? `Saved boards (${boardCount})` : "Saved boards"}
      </button>

      <button className="ghost wide" onClick={onHelp}>
        Guides &amp; help
      </button>

      <details className="home-item">
        <summary>Settings</summary>
        <div className="home-body">
          <label className="field inline">
            <span>Price the worst matchup</span>
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
          <p className="hint">
            Pricing a dodge takes a solve, so <em>When I ask</em> and{" "}
            <em>Never</em> both skip the work rather than computing it and hiding
            the answer.
          </p>
          <label className="field inline">
            <span>Advice during a round</span>
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
          <p className="hint">
            The picks and their numbers never change &mdash; this only sets how
            much the round explains itself. <em>Just the picks</em> drops the
            reasoning for a faster read; <em>No advice</em> shows the bare
            options.
          </p>
          <label className="field inline">
            <span>Show numbers as</span>
            <select
              value={roundUnit}
              onChange={(e) => onRoundUnit(e.target.value as Unit)}
            >
              {ROUND_UNITS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <p className="hint">
            One currency for the whole round screen. <em>Round-win %</em> is the
            chance of taking the round from the position a tap would create;{" "}
            <em>Rating points</em> is the guaranteed total in the numbers you
            wrote on the grid. The recommendation is the same either way &mdash;
            only the figures change.
          </p>
          <label className="field inline">
            <span>Surprise-pick alerts</span>
            <select
              value={surpriseMode}
              onChange={(e) => onSurpriseMode(e.target.value as SurpriseMode)}
            >
              {SURPRISE_MODES.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline">
            <span>Surprise threshold (regret)</span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={Number.isFinite(surpriseRegretThreshold) ? surpriseRegretThreshold : 0}
              onChange={(e) => onSurpriseRegretThreshold(Number(e.target.value))}
            />
          </label>
          <p className="hint">
            Experimental. Alerts fire when an opponent move gives up at least this
            many points versus your grid&apos;s expected best move.
          </p>
        </div>
      </details>

      <details className="home-item">
        <summary>Back up and restore</summary>
        <div className="home-body">
          <LongshanksImport onImported={onRestored} />
          <BoardBackup onRestored={onRestored} />
        </div>
      </details>

      <details className="home-item">
        <summary>How it works</summary>
        <div className="home-body">
          <p className="hint">
            Rate every matchup on your grid, worst to best. The app then plays
            out the nomination sequence assuming the opponent answers as well as
            they possibly could, and reports the round total you are{" "}
            <strong>guaranteed</strong> even against that -- not the total you
            might get if things go your way.
          </p>
          <p className="hint">
            <strong>Guaranteed</strong> is the floor: it assumes their grid is
            the mirror of yours. <strong>Typical</strong> is what a real opposing
            board tends to produce. Use the floor when you must not lose, the
            typical when you must win.
          </p>
          <p className="hint">
            During a round, open <em>Round</em> and log each nomination as it
            happens. The advice narrows as the board empties, because there is
            less left to go wrong.
          </p>
        </div>
      </details>

      <details className="home-item">
        <summary>About</summary>
        <div className="home-body">
          <p className="hint">
            {BRAND.product} &mdash; {BRAND.tagline}. Everything is stored on this
            device only; nothing is uploaded, and it all works with no signal.
          </p>
          <p className="hint">
            The raven and the {BRAND.name} wordmark are placeholders.
          </p>
        </div>
      </details>

      <div className="home-links">
        <a className="ghost wide" href={LINKS.bugs} target="_blank" rel="noreferrer">
          Log a bug
        </a>
        {/*
          Rendered only when there is somewhere for it to go. A button that
          silently does nothing is worse at a table than no button at all.
        */}
        {LINKS.beer && (
          <a className="ghost wide" href={LINKS.beer} target="_blank" rel="noreferrer">
            Buy me a beer
          </a>
        )}
      </div>
    </div>
  );
}
