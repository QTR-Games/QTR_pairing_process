import { useMemo, useState } from "react";
import type { Matrix } from "../engine/boardAnalysis";
import type { Decision, LiveState, MoveOption, OptionProfile, PickOption } from "../engine/live";
import {
  commitPairing,
  currentDecision,
  liveWinChance,
  moveOptions,
  optionProfile,
  optionProfileBy,
  pickOptions,
  pickTieBreak,
  playerLeverage,
  playerLeverageBy,
  setCommittedTable,
} from "../engine/live";
import { solveCache, type SolveCache } from "../engine/protocol";
import { toWinProbability } from "../engine/winProbability";
import type { Board } from "../model/board";
import { boardMatrix, boardScale } from "../model/board";
import { useLongPress } from "../hooks/useLongPress";
import { gapInUnit, inUnit, pct, points } from "../model/format";
import { ratingColor, toFraction, type Scale } from "../model/scale";
import type { AdviceLevel, SurpriseMode, TableTracking, Unit } from "../model/settings";

interface Props {
  board: Board;
  state: LiveState;
  onState: (s: LiveState) => void;
  onReset: () => void;
  /**
   * Step the round back one action. Optional so the many tests and callers
   * that drive the panel without a history stack keep the flow they had; the
   * control only appears when there is something wired up to handle it.
   */
  onUndo?: () => void;
  /** Whether there is a previous state to step back to. */
  canUndo?: boolean;
  /**
   * How much the round explains itself. Defaults to full: the engine does the
   * same search either way, so a caller that never sets this gets every "why"
   * exactly as before, which is what the live-round tests rely on.
   */
  adviceLevel?: AdviceLevel;
  surpriseMode?: SurpriseMode;
  surpriseRegretThreshold?: number;
  /**
   * The currency every number on this screen reads in. Defaults to chance, the
   * currency the rest of the app speaks, so a caller that never sets it gets
   * the round-win view the live-round tests rely on.
   */
  roundUnit?: Unit;
  /**
   * Whether locking in a pairing offers a table popup before the next
   * decision. Defaults to off, so a caller that never sets it -- including
   * the tap-through e2e suite, which asserts every option against the engine
   * as an oracle -- sees exactly the commit-and-advance flow it always did.
   */
  tableTracking?: TableTracking;
}

/**
 * The live state that results from taking a non-pair option -- nominating a
 * player (open) or playing the only legal pairing (forced). Mirrors what
 * `applyOpen` and the forced tap commit, so a card's projected round-win chance
 * is priced against exactly the position the tap would create.
 */
function optionState(
  matrix: Matrix,
  s: LiveState,
  decision: Decision,
  opt: MoveOption,
): LiveState | null {
  if (decision.kind === "forced" && opt.ours !== undefined && opt.theirs !== undefined) {
    return commitPairing(matrix, s, opt.ours, opt.theirs, null, null);
  }
  if (decision.kind === "open" && decision.owner === "our" && opt.ours !== undefined) {
    return { ...s, ourPool: s.ourPool & ~(1 << opt.ours), attacker: opt.ours, attackerSide: "our" };
  }
  if (decision.kind === "open" && decision.owner === "their" && opt.theirs !== undefined) {
    return {
      ...s,
      theirPool: s.theirPool & ~(1 << opt.theirs),
      attacker: opt.theirs,
      attackerSide: "their",
    };
  }
  return null;
}

/** The live state that results from taking one half of an offered pair. */
function pickState(
  matrix: Matrix,
  s: LiveState,
  pair: [number, number],
  picked: number,
): LiveState {
  const leftover = picked === pair[0] ? pair[1] : pair[0];
  const attackerIsUs = s.attackerSide === "our";
  const [ours, theirs] = attackerIsUs ? [s.attacker, picked] : [picked, s.attacker];
  return commitPairing(matrix, s, ours, theirs, leftover, attackerIsUs ? "their" : "our");
}

/**
 * Guaranteed round-win chance if a given option is taken, in [0, 1].
 *
 * The currency of the rest of the app, brought to the live tree. For an offer
 * the value is the one the *attacker* realises: they pick the half that suits
 * them, so it is the best of the two halves for us when we hold the attacker and
 * the worst when they do -- exactly what the two pick tiles beneath it show.
 */
function optionChanceValue(
  matrix: Matrix,
  s: LiveState,
  decision: Decision,
  opt: MoveOption,
  chanceOf: (st: LiveState) => number,
): number {
  if (opt.pair) {
    const attackerIsUs = s.attackerSide === "our";
    const ca = chanceOf(pickState(matrix, s, opt.pair, opt.pair[0]));
    const cb = chanceOf(pickState(matrix, s, opt.pair, opt.pair[1]));
    return attackerIsUs ? Math.max(ca, cb) : Math.min(ca, cb);
  }
  const st = optionState(matrix, s, decision, opt);
  return st ? chanceOf(st) : 0;
}

interface SurpriseNotice {
  regret: number;
  valueDelta: number;
  chanceBest: number;
  chanceAfter: number;
  priorityBefore: number | null;
  priorityAfter: number | null;
}

const priorityNow = (leverage: ReturnType<typeof playerLeverage>): number | null =>
  leverage.length > 0 ? leverage[leverage.length - 1].player : null;

/**
 * The round, as it happens.
 *
 * Every option is tappable, including the ones the engine rates as mistakes,
 * because the opponent does not consult us before moving. Recording what they
 * actually did is the whole point: the advice for the rest of the round is
 * recomputed from the real position, not from the one we predicted.
 *
 * That is the direct answer to being bussed in 2024. A side that throws a
 * player away to set up later matchups is not making a random move, it is
 * making a move that looks bad on this pairing and good on the next three. The
 * search sees the next three.
 */
export function LivePanel({
  board,
  state,
  onState,
  onReset,
  onUndo,
  canUndo = false,
  adviceLevel = "full",
  surpriseMode = "off",
  surpriseRegretThreshold = 0,
  roundUnit = "chance",
  tableTracking = "off",
}: Props) {
  const scale = boardScale(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);

  // The toggle draws two lines through the same computed advice. `showProse` is
  // the paragraphs -- tie-break reasoning, hold-or-play, upside-if-they-err;
  // `showHints` is the one-line recommendation and the tags. Full shows both,
  // brief keeps only the hints, off shows neither and leaves the bare options.
  const showProse = adviceLevel === "full";
  const showHints = adviceLevel !== "off";

  const decision = useMemo(() => currentDecision(state), [state]);

  /*
   * One search shared by everything on this screen.
   *
   * The solver memo keys on the whole pairing state and not on the board, so a
   * cache stays valid for as long as the board does -- across every option row,
   * across every profile, and across every tap for the rest of the round. It is
   * scoped to `matrix` so a board edit throws it away, which is exactly when it
   * stops being correct.
   *
   * Measured on the perf harness: a whole round drops from 26.7 ms to 17.6 ms
   * (1.9x on the openings), for identical advice. Before this, `moveOptions`
   * allocated a fresh memo per call and was re-entered once by `playerLeverage`
   * and once per option by `optionProfile`.
   */
  const cache = useMemo(() => solveCache(matrix), [matrix]);

  /*
   * Round-win chance is the currency the rest of the app reads in, so the live
   * tree shows it too. `liveWinChance` searches the same decision tree the
   * points engine does; a shared memo lets one render price every option and
   * pick tile without repeating the walk. Scoped to the board (and its scale)
   * so a board edit throws it away, exactly like the points cache above.
   */
  const chanceOf = useMemo(() => {
    const memo = new Map<string, number>();
    return (st: LiveState) => liveWinChance(matrix, st, scale.min, scale.max, memo);
  }, [matrix, scale.min, scale.max]);

  const rawOptions = useMemo(() => moveOptions(matrix, state, cache), [matrix, state, cache]);
  const leverage = useMemo(() => playerLeverage(matrix, state, cache), [matrix, state, cache]);

  /** Print a value the engine has already priced in the displayed currency. */
  const show = (v: number) => inUnit(roundUnit, v);

  /** A matchup rating, in the displayed currency: the number written, or its win chance. */
  const ratingValue = (r: number) =>
    roundUnit === "chance" ? toWinProbability(r, scale.min, scale.max) : r;

  /*
   * The chance valuation of an option, in the shape the engine's generic
   * leverage and profile helpers ask for. `from` rather than the panel's own
   * state because a profile prices *their replies* to a position one move
   * deeper, and the decision that option belongs to is the one at that node.
   */
  const chanceValueOf = useMemo(
    () => (o: MoveOption, from: LiveState) =>
      optionChanceValue(matrix, from, currentDecision(from), o, chanceOf),
    [matrix, chanceOf],
  );

  /*
   * Hold-or-play in the displayed currency.
   *
   * Ranked by the number it prints: the panel is a sorted list, and sorting it
   * on points while showing chance would put a smaller figure above a larger
   * one. The points list is still computed above because the surprise flag's
   * priority seat reads from it, and that must not move when a display toggle
   * is flipped.
   */
  const leverageShown = useMemo(
    () =>
      roundUnit === "points"
        ? leverage
        : playerLeverageBy(matrix, state, chanceValueOf, cache),
    [roundUnit, leverage, matrix, state, chanceValueOf, cache],
  );

  /*
   * When several of our options carry the same guaranteed value, minimax has
   * nothing left to say and the app would otherwise present a coin flip. The
   * profile looks at the same options across every reply they have, which
   * separates them on 24 of the 28 real 2024 boards where the top openers tie.
   *
   * Options are then ranked by guaranteed value first -- never trade the floor
   * away -- and only among equals by upside, then by how few replies punish it.
   *
   * Profiles are computed whether or not anything ties. Finding 20 measured the
   * two halves of the decision apart across all 31 real boards: the spread our
   * own choice controls is a median of 0.00 and never exceeds 1.0, while the
   * spread across their replies runs to 2.0. Their reply is the bigger number
   * even on boards where our choice does separate, so "up to X if they misstep"
   * is worth showing on a clear winner too, not only on a coin flip.
   */
  const ranked = useMemo(() => {
    const ours = "owner" in decision && decision.owner === "our";
    const plain = rawOptions.map((o) => ({ o, p: undefined as OptionProfile | undefined }));
    if (!ours || rawOptions.length === 0) return plain;

    const withProfiles = rawOptions.map((o) => ({
      o,
      p: optionProfile(matrix, state, o, cache) ?? undefined,
    }));

    withProfiles.sort(
      (a, b) =>
        b.o.value - a.o.value ||
        (b.p?.upside ?? 0) - (a.p?.upside ?? 0) ||
        (a.p?.punishingReplies ?? 0) - (b.p?.punishingReplies ?? 0),
    );
    return withProfiles;
  }, [matrix, state, rawOptions, decision, cache]);

  /*
   * Every option with a profile in the displayed currency attached.
   *
   * `ranked` above is deliberately left alone: it is priced in points and it
   * decides both the order and which option is called best. Flipping the
   * display unit must never move the recommendation, only the figures printed
   * beside it -- so the chance profile is computed as a second, parallel read
   * of the same options rather than by re-ranking them.
   */
  const rows = useMemo(
    () =>
      ranked.map(({ o, p }) => ({
        o,
        p,
        pShown:
          roundUnit === "points" || !p
            ? p
            : (optionProfileBy(matrix, state, o, chanceValueOf, cache) ?? undefined),
        chance: optionChanceValue(matrix, state, decision, o, chanceOf),
      })),
    [ranked, roundUnit, matrix, state, cache, chanceValueOf, decision, chanceOf],
  );

  const tieBreak = useMemo(() => summariseTieBreak(rows, roundUnit), [rows, roundUnit]);

  // The owner's optimum in the same currency the cards read in, so every card's
  // "how far behind the best offer" tag is a chance gap rather than a points
  // one. The list is ranked on the points floor, so the top row is the
  // reference; a card that happens to price higher in chance simply reads level.
  const bestChance = rows.length > 0 ? rows[0].chance : 0;

  const ourName = (i: number) => board.ourPlayers[i] ?? `Us ${i + 1}`;
  const theirName = (i: number) => board.theirPlayers[i] ?? `Them ${i + 1}`;

  const ownerIsUs = "owner" in decision && decision.owner === "our";
  const [surprise, setSurprise] = useState<SurpriseNotice | null>(null);

  const surpriseEnabled = surpriseMode === "on";
  const surpriseThreshold = Math.max(0, surpriseRegretThreshold);

  /*
   * A pairing that has been decided but not yet handed to `onState`, because
   * the table popup is still open on it. Held here rather than committed
   * straight away so the round genuinely pauses on this decision -- advancing
   * to the next nomination before the table is chosen is the exact lapse the
   * feature exists to catch.
   */
  const [pendingTable, setPendingTable] = useState<{
    next: LiveState;
    ours: number;
    theirs: number;
  } | null>(null);
  /*
   * The index of an already-committed pairing whose table is being set or
   * changed after the fact. Skip exists so an unknown table never traps you on
   * the popup, which only works if the table can still be filled in once you
   * know it -- otherwise skipping silently discards it for the rest of the
   * round. Reuses the same sheet as `pendingTable`; the two are never both set.
   */
  const [editingTable, setEditingTable] = useState<number | null>(null);
  const [tableInput, setTableInput] = useState("");
  const [copyNote, setCopyNote] = useState<string | null>(null);

  /** Commit a pairing, pausing on a table prompt first when tracking is on. */
  function commitWithTable(next: LiveState, ours: number, theirs: number) {
    if (tableTracking === "on") {
      setTableInput("");
      setPendingTable({ next, ours, theirs });
    } else {
      onState(next);
    }
  }

  /** Resolve the table popup: `table` is null for the skip button. */
  function resolvePendingTable(table: string | null) {
    if (!pendingTable) return;
    const idx = pendingTable.next.committed.length - 1;
    onState(table ? setCommittedTable(pendingTable.next, idx, table) : pendingTable.next);
    setPendingTable(null);
    setTableInput("");
  }

  /** Open the same sheet against a pairing that is already locked in. */
  function openTableEditor(index: number) {
    setTableInput(state.committed[index]?.table ?? "");
    setEditingTable(index);
  }

  /** Resolve the editor: `table` is null to clear a table that was set. */
  function resolveEditingTable(table: string | null) {
    if (editingTable === null) return;
    onState(setCommittedTable(state, editingTable, table));
    setEditingTable(null);
    setTableInput("");
  }

  /** Dismiss whichever of the two the sheet is currently open for. */
  function dismissSheet() {
    if (pendingTable) resolvePendingTable(null);
    else setEditingTable(null);
  }

  /** The pairing the sheet is open against, whichever path opened it. */
  const sheetPair = pendingTable
    ? { ours: pendingTable.ours, theirs: pendingTable.theirs }
    : editingTable !== null && state.committed[editingTable]
      ? { ours: state.committed[editingTable].ours, theirs: state.committed[editingTable].theirs }
      : null;

  /** Sheet's primary action: commit the typed table down whichever path is open. */
  function submitTable(table: string | null) {
    if (pendingTable) resolvePendingTable(table);
    else resolveEditingTable(table);
  }

  /**
   * Sheet's secondary action. On a fresh commit that is "skip" and must leave
   * the pairing alone; on an existing row it is "clear", which has to write the
   * null through so a table set by mistake can actually be removed.
   */
  function dismissClear() {
    if (pendingTable) resolvePendingTable(null);
    else resolveEditingTable(null);
  }

  /** Copy the "Tables set" list, one pairing per line, to the clipboard. */
  async function copyCommitted() {
    const lines = state.committed.map((c) => {
      const pair = `${ourName(c.ours)} vs ${theirName(c.theirs)}`;
      return c.table ? `${pair} — Table ${c.table}` : pair;
    });
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopyNote("Copied.");
    } catch {
      setCopyNote("Could not reach the clipboard.");
    }
  }
  const copyPress = useLongPress(copyCommitted);

  const checkSurprise = (
    before: LiveState,
    after: LiveState,
    bestAfter: LiveState,
    chosenValue: number,
    bestValue: number,
    regretLoss: number,
  ) => {
    if (!surpriseEnabled || regretLoss <= 1e-9 || regretLoss < surpriseThreshold) {
      setSurprise(null);
      return;
    }
    const chanceBest = liveWinChance(matrix, bestAfter, scale.min, scale.max);
    const chanceAfter = liveWinChance(matrix, after, scale.min, scale.max);
    const beforePriority = priorityNow(playerLeverage(matrix, before, cache));
    const afterPriority = priorityNow(playerLeverage(matrix, after, cache));
    setSurprise({
      regret: regretLoss,
      valueDelta: chosenValue - bestValue,
      chanceBest,
      chanceAfter,
      priorityBefore: beforePriority,
      priorityAfter: afterPriority,
    });
  };

  function applyOpen(playerIndex: number, owner: "our" | "their") {
    const next = {
      ...state,
      ourPool: owner === "our" ? state.ourPool & ~(1 << playerIndex) : state.ourPool,
      theirPool: owner === "their" ? state.theirPool & ~(1 << playerIndex) : state.theirPool,
      attacker: playerIndex,
      attackerSide: owner,
    };
    if (owner === "their") {
      const chosen = rawOptions.find((o) => o.theirs === playerIndex);
      const best = rawOptions[0];
      const bestNext =
        best?.theirs !== undefined
          ? {
              ...state,
              theirPool: state.theirPool & ~(1 << best.theirs),
              attacker: best.theirs,
              attackerSide: "their" as const,
            }
          : null;
      if (chosen && best && bestNext) {
        checkSurprise(state, next, bestNext, chosen.value, best.value, Math.abs(chosen.regret));
      } else {
        setSurprise(null);
      }
    } else {
      setSurprise(null);
    }
    onState(next);
  }

  /** Record which of an offered pair was taken. */
  function applyPick(pair: [number, number], picked: number, offer: MoveOption) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const attackerIsUs = state.attackerSide === "our";
    const [ours, theirs] = attackerIsUs
      ? [state.attacker, picked]
      : [picked, state.attacker];
    const next = commitPairing(matrix, state, ours, theirs, leftover, attackerIsUs ? "their" : "our");
    if (decision.kind === "offer" && decision.owner === "their") {
      const best = rawOptions[0];
      const bestPair = best?.pair;
      if (bestPair) {
        const bestPicks = pickOptions(matrix, state, bestPair, cache);
        const bestPicked = bestPicks.reduce((acc, p) => (p.value > acc.value ? p : acc), bestPicks[0]);
        const bestLeftover = bestPicked.player === bestPair[0] ? bestPair[1] : bestPair[0];
        const bestAfter = commitPairing(
          matrix,
          state,
          state.attacker,
          bestPicked.player,
          bestLeftover,
          "their",
        );
        checkSurprise(state, next, bestAfter, offer.value, best.value, Math.abs(offer.regret));
      } else setSurprise(null);
    } else if (decision.kind === "offer" && decision.attackerSide === "their") {
      const picks = pickOptions(matrix, state, pair, cache);
      const chosen = picks.find((p) => p.player === picked);
      const bestValue = Math.min(...picks.map((p) => p.value));
      const bestPick = picks.reduce((acc, p) => (p.value < acc.value ? p : acc), picks[0]);
      const bestLeftover = bestPick.player === pair[0] ? pair[1] : pair[0];
      const bestAfter = commitPairing(matrix, state, bestPick.player, state.attacker, bestLeftover, "our");
      if (chosen) {
        checkSurprise(state, next, bestAfter, chosen.value, bestValue, Math.abs(chosen.value - bestValue));
      } else {
        setSurprise(null);
      }
    } else {
      setSurprise(null);
    }
    commitWithTable(next, ours, theirs);
  }

  return (
    <section className="live">
      <header className="live-head">
        <div>
          <h2>{prompt(decision, ourName, theirName)}</h2>
          <p className="live-sub">
            {state.committed.length} of {board.ourPlayers.length} tables set
            {" "}&middot;{" "}
            {roundUnit === "chance"
              ? `${pct(chanceOf(state))} to take the round`
              : `${points(rawOptions[0]?.value ?? state.banked)} guaranteed`}
          </p>
        </div>
        <div className="live-actions">
          {onUndo && (
            <button
              type="button"
              className="ghost"
              onClick={onUndo}
              disabled={!canUndo}
              aria-label="Undo the last pairing action"
            >
              Back
            </button>
          )}
          <button type="button" className="ghost" onClick={onReset}>
            Restart
          </button>
        </div>
      </header>

      {decision.kind === "done" ? (
        <Result state={state} chance={chanceOf(state)} scale={scale} unit={roundUnit} ourName={ourName} theirName={theirName} />
      ) : (
        <>
          {showProse && tieBreak && (
            <div className="tiebreak">
              <p className="tiebreak-lead">{tieBreak.lead}</p>
              <p className="tiebreak-body">{tieBreak.body}</p>
            </div>
          )}
          {surprise && (
            <div className="surprise-flag" role="alert">
              <p className="surprise-lead">
                !!! Opponent previous choice is suspiciously outside expectations. Be careful!
              </p>
              <p className="surprise-body">
                They gave up {points(surprise.regret)} points against your model ({points(surprise.valueDelta)} to
                the floor), moving your projected round-win chance from {pct(surprise.chanceBest)} to{" "}
                {pct(surprise.chanceAfter)}. Why might they choose this line?
                {surprise.priorityAfter === null && surprise.priorityBefore === null
                  ? ""
                  : surprise.priorityBefore !== surprise.priorityAfter
                    ? ` Recheck priority now: ${ourName(surprise.priorityAfter ?? surprise.priorityBefore!)} moved into the commit-now seat.`
                    : ` Priority still points at ${ourName(surprise.priorityAfter!)}.`}
              </p>
            </div>
          )}

          <ol className="options">
            {rows.map(({ o, pShown }, idx) => (
              <OptionRow
                key={idx}
                option={o}
                profile={pShown}
                decision={decision}
                matrix={matrix}
                state={state}
                cache={cache}
                best={idx === 0}
                ownerIsUs={ownerIsUs}
                bestChance={bestChance}
                chanceOf={chanceOf}
                ratingSpan={scale.max - scale.min}
                scale={scale}
                showProse={showProse}
                showHints={showHints}
                roundUnit={roundUnit}
                ourName={ourName}
                theirName={theirName}
                onChoose={() => {
                  if (decision.kind === "open") {
                    applyOpen(
                      decision.owner === "our" ? o.ours! : o.theirs!,
                      decision.owner,
                    );
                  } else if (decision.kind === "forced") {
                    setSurprise(null);
                    commitWithTable(
                      commitPairing(matrix, state, o.ours!, o.theirs!, null, null),
                      o.ours!,
                      o.theirs!,
                    );
                  }
                }}
                onPick={(picked) => applyPick(o.pair!, picked, o)}
              />
            ))}
          </ol>

          {showProse && leverageShown.length > 1 && (
            <Leverage leverage={leverageShown} unit={roundUnit} ourName={ourName} />
          )}
        </>
      )}

      {state.committed.length > 0 && (
        <div
          className="committed"
          onContextMenu={(e) => {
            e.preventDefault();
            copyCommitted();
          }}
        >
          <div className="committed-head" {...copyPress}>
            <h3>Tables set</h3>
            <button
              type="button"
              className="ghost small"
              onClick={(e) => {
                e.stopPropagation();
                copyCommitted();
              }}
              aria-label="Copy tables set to clipboard"
            >
              Copy
            </button>
          </div>
          <ul>
            {state.committed.map((c, i) => (
              <CommittedRow
                key={i}
                pair={`${ourName(c.ours)} vs ${theirName(c.theirs)}`}
                table={c.table}
                onEdit={() => openTableEditor(i)}
              >
                <strong>{show(ratingValue(c.value))}</strong>
              </CommittedRow>
            ))}
          </ul>
          <p className="hint">Hold a pairing to set or change its table.</p>
          {copyNote && <p className="hint copy-note">{copyNote}</p>}
        </div>
      )}

      {sheetPair && (
        <div className="sheet-backdrop" role="presentation" onClick={dismissSheet}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <p className="sheet-title">
              {ourName(sheetPair.ours)}
              <span className="vs"> vs </span>
              {theirName(sheetPair.theirs)}
            </p>
            <label className="field inline">
              <span>Table</span>
              <input
                type="text"
                inputMode="numeric"
                autoFocus
                value={tableInput}
                onChange={(e) => setTableInput(e.target.value)}
                placeholder="e.g. 5"
              />
            </label>
            <p className="sheet-hint">
              {pendingTable
                ? "Which table did this matchup take? Skip if you do not know yet -- hold the pairing under \u201cTables set\u201d to fill it in later."
                : "Which table did this matchup take? Clear leaves it unset."}
            </p>
            <div className="table-prompt-actions">
              <button type="button" className="ghost wide" onClick={dismissClear}>
                {pendingTable ? "Skip" : "Clear"}
              </button>
              <button
                type="button"
                className="primary wide"
                onClick={() => submitTable(tableInput.trim() || null)}
              >
                Set table
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

/**
 * One locked-in pairing under "Tables set".
 *
 * Hold-to-edit rather than tap-to-edit for the reason `useLongPress` exists:
 * this list sits at the bottom of the round screen under a thumb that brushes
 * it while scrolling, and a stray tap that reopened the table sheet mid-round
 * would be worse than no shortcut at all. Right-click is the desktop
 * equivalent, and it stops propagating so it does not also trip the copy
 * handler on the surrounding block.
 */
function CommittedRow({
  pair,
  table,
  onEdit,
  children,
}: {
  pair: string;
  table: string | null;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  const press = useLongPress(onEdit);
  return (
    <li>
      <span
        className="committed-pair"
        role="button"
        tabIndex={0}
        aria-label={
          table ? `${pair}, table ${table}. Change table.` : `${pair}, no table set. Set table.`
        }
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onEdit();
        }}
        {...press}
      >
        {pair}
        {table && <span className="table-tag"> — Table {table}</span>}
      </span>
      {children}
    </li>
  );
}

function prompt(
  d: ReturnType<typeof currentDecision>,
  ourName: (i: number) => string,
  theirName: (i: number) => string,
): string {
  switch (d.kind) {
    case "open":
      return d.owner === "our" ? "Put a player up" : "Which player did they put up?";
    case "offer":
      return d.owner === "our"
        ? `Offer two against ${theirName(d.attacker)}`
        : `What two did they offer against ${ourName(d.attacker)}?`;
    case "forced":
      return `${ourName(d.ours)} vs ${theirName(d.theirs)} — forced`;
    default:
      return "Round complete";
  }
}

function OptionRow({
  option,
  profile,
  decision,
  matrix,
  state,
  cache,
  best,
  ownerIsUs,
  bestChance,
  chanceOf,
  ratingSpan,
  scale,
  showProse,
  showHints,
  roundUnit,
  ourName,
  theirName,
  onChoose,
  onPick,
}: {
  option: MoveOption;
  profile?: OptionProfile;
  decision: ReturnType<typeof currentDecision>;
  matrix: Matrix;
  state: LiveState;
  /** The panel's board-scoped search cache, shared by every row. */
  cache: SolveCache;
  best: boolean;
  ownerIsUs: boolean;
  /** The owner's optimum round-win chance, for pricing this card's shortfall. */
  bestChance: number;
  /** Prices a resulting live state in round-win chance, memoised per render. */
  chanceOf: (st: LiveState) => number;
  /** `scale.max - scale.min`; the tie-break threshold is a fraction of it. */
  ratingSpan: number;
  /** The board scale, for colouring raw matchup-rating chips on each tile. */
  scale: Scale;
  /** Show the explanatory paragraphs (full only). */
  showProse: boolean;
  /** Show the one-line recommendation and the tags (full and brief). */
  showHints: boolean;
  /** The currency every figure on this row prints in. */
  roundUnit: Unit;
  ourName: (i: number) => string;
  theirName: (i: number) => string;
  onChoose: () => void;
  onPick: (picked: number) => void;
}) {
  // Everything the captain reads off a card is priced in round-win chance, the
  // currency the rest of the app already speaks. `wins` is being the favourite
  // rather than clearing a points threshold; `cost` is the chance surrendered
  // against the best offer, and rounds to nothing when the two are level.
  const optionChance = optionChanceValue(matrix, state, decision, option, chanceOf);
  const wins = optionChance > 0.5;
  const cost = Math.max(0, ownerIsUs ? bestChance - optionChance : optionChance - bestChance);

  // The same two readings in the currency on show. `regret` is the engine's own
  // points shortfall against the best move, so the points column never has to
  // re-derive what the search already knew.
  const show = (v: number) => inUnit(roundUnit, v);
  const ratingValue = (r: number) =>
    roundUnit === "chance" ? toWinProbability(r, scale.min, scale.max) : r;
  const shownValue = roundUnit === "chance" ? optionChance : option.value;
  const shownCost = roundUnit === "chance" ? cost : Math.abs(option.regret);
  const level = roundUnit === "chance" ? cost < 0.005 : shownCost < 1e-9;

  if (option.pair) {
    // An offer is two taps: what was offered, then which one was taken.
    const attackerSide = "attackerSide" in decision ? decision.attackerSide : "our";
    const names = attackerSide === "our" ? theirName : ourName;
    // When we hold the attacker, choosing between the two halves is OUR
    // decision, so it needs the same numbers as any other decision of ours.
    const choiceIsOurs = attackerSide === "our";
    const picks = pickOptions(matrix, state, option.pair, cache);
    // The raw matchup rating for a tile: what OUR grid scored this exact pairing.
    // When we hold the attacker, our fixed player faces each of their offered
    // two, so the rating is our attacker's row against that column. When they
    // hold the attacker, each tile is one of our players against their fixed
    // attacker. Either way it is the number the captain wrote, surfaced so he
    // can decide to pivot off the projected score when a player rates the
    // matchup very high or very low.
    const ratingFor = (player: number) =>
      choiceIsOurs ? matrix[state.attacker][player] : matrix[player][state.attacker];
    // Every row, not just the recommended one: *they* choose which pair to
    // offer, so the row the user actually faces is not the row we would have
    // picked for them. Advising only the recommendation leaves the real
    // decision unlabelled.
    //
    // Affordable because `pickTieBreak` returns before sampling anything unless
    // the floor ties, and only 43% of rows do. Measured over the five real WTC
    // boards, the whole list costs a median of 29ms and at worst 92ms.
    const tieBreak =
      choiceIsOurs && Math.abs(picks[0].value - picks[1].value) < 1e-9
        ? pickTieBreak(matrix, state, option.pair, ratingSpan, cache)
        : null;
    const highlight = (p: PickOption): boolean => {
      if (!choiceIsOurs) return false;
      // Interchangeable means neither is preferred, so marking one would be a
      // claim the engine explicitly declined to make.
      if (tieBreak?.reason === "interchangeable") return false;
      if (tieBreak) return p.player === tieBreak.player;
      return p.best && Math.abs(picks[0].value - picks[1].value) > 1e-9;
    };
    // What both halves hold. They tie exactly in points -- that is what puts
    // this paragraph on screen -- but their chance values need not tie, so in
    // that currency the shared claim is the weaker of the two, and the wording
    // says "at least" to stay true either way.
    const bothHold =
      roundUnit === "chance"
        ? Math.min(
            ...picks.map((p) => chanceOf(pickState(matrix, state, option.pair!, p.player))),
          )
        : picks[0].value;
    const bothHoldText =
      roundUnit === "chance" ? `at least ${show(bothHold)}` : show(bothHold);
    return (
      <li className={"option" + (best ? " best" : "")}>
        <div className="option-main">
          <span className="option-label">
            {names(option.pair[0])} or {names(option.pair[1])}
          </span>
          <span className={"option-value" + (wins ? " winning" : "")}>{show(shownValue)}</span>
        </div>
        <div className="option-meta">
          {showHints &&
            (best ? (
              <span className="tag">
                {ownerIsUs ? "best offer" : "their strongest"}
              </span>
            ) : !level ? (
              <span className="tag cost">-{show(shownCost)}</span>
            ) : (
              <span className="tag cost">same floor</span>
            ))}
        </div>
        <div className="pick-row">
          {picks.map((p) => {
            const pickChance = chanceOf(pickState(matrix, state, option.pair!, p.player));
            const rating = ratingFor(p.player);
            return (
            <button
              key={p.player}
              type="button"
              className={"pick" + (showHints && highlight(p) ? " pick-best" : "")}
              onClick={() => onPick(p.player)}
            >
              <span className="pick-name">
                {names(p.player)} {choiceIsOurs ? "" : "played"}
              </span>
              <span
                className="pick-rating"
                style={{ background: ratingColor(toFraction(rating, scale)) }}
                // The raw number the captain wrote stays reachable on the chip
                // even when the screen is reading in chance, because it is the
                // one figure he can check against his own sheet.
                title={`${choiceIsOurs ? "Our" : "Their"} rating of this matchup: ${points(rating)}`}
              >
                {show(ratingValue(rating))}
              </span>
              <span className={"pick-value" + (pickChance > 0.5 ? " winning" : "")}>
                {show(roundUnit === "chance" ? pickChance : p.value)}
              </span>
            </button>
            );
          })}
        </div>
        {choiceIsOurs && showHints && (
          <p className="pick-hint">
            {picks[0].value !== picks[1].value ? (
              <>Take {names(picks.find((p) => p.best)!.player)}.</>
            ) : !showProse ? (
              tieBreak?.reason === "interchangeable" ? (
                <>Level on the numbers &mdash; genuinely your call.</>
              ) : tieBreak ? (
                <>
                  Level on the numbers; edge to{" "}
                  <strong>{names(tieBreak.player)}</strong>.
                </>
              ) : (
                <>Level on the numbers &mdash; your call.</>
              )
            ) : tieBreak?.reason === "interchangeable" ? (
              <>
                Both hold {bothHoldText}, and your grid rates{" "}
                {names(tieBreak.player)} and {names(tieBreak.other)} the same
                against everyone you have left &mdash; so this is genuinely
                yours to call. Pick on what the sheet cannot see: terrain, who
                wants the table, who is on form.
              </>
            ) : tieBreak ? (
              <>
                Both hold {bothHoldText}. Take{" "}
                <strong>{names(tieBreak.player)}</strong> &mdash;{" "}
                {tieBreak.reason === "typical" ? (
                  roundUnit === "chance" ? (
                    <>
                      if they play their own board it typically comes out ahead
                      of {names(tieBreak.other)}.
                    </>
                  ) : (
                    <>
                      if they play their own board it leaves {points(tieBreak.value)}{" "}
                      reachable against {points(tieBreak.otherValue)}.
                    </>
                  )
                ) : tieBreak.reason === "upside" ? (
                  roundUnit === "chance" ? (
                    <>
                      same floor either way, but it keeps more alive if they
                      misplay. Play to your outs.
                    </>
                  ) : (
                    <>
                      same floor either way, but it keeps {points(tieBreak.value)} alive
                      if they misplay against {points(tieBreak.otherValue)}. Play to
                      your outs.
                    </>
                  )
                ) : tieBreak.reason === "average" ? (
                  roundUnit === "chance" ? (
                    <>
                      floor, ceiling and pressure all match, but across their
                      whole reply space it averages higher.
                    </>
                  ) : (
                    <>
                      floor, ceiling and pressure all match, but across their whole
                      reply space it averages {points(tieBreak.value)} against{" "}
                      {points(tieBreak.otherValue)}.
                    </>
                  )
                ) : (
                  <>
                    same floor and same upside, but only{" "}
                    {pct(tieBreak.value)} of their replies hold you
                    there, against {pct(tieBreak.otherValue)}.
                  </>
                )}
              </>
            ) : (
              <>
                Both hold {bothHoldText} and every measure this app has
                comes out level &mdash; but they are not the same players, so
                there is an edge here the grid is not capturing. Trust what you
                know about the matchup.
              </>
            )}
          </p>
        )}
      </li>
    );
  }

  const label =
    option.ours !== undefined && option.theirs !== undefined
      ? `${ourName(option.ours)} vs ${theirName(option.theirs)}`
      : option.ours !== undefined
        ? ourName(option.ours)
        : theirName(option.theirs!);

  // A forced pairing has both sides fixed, so it has one concrete matchup
  // rating from our grid. Open moves (one side only) have no fixed opponent yet.
  const concreteRating =
    option.ours !== undefined && option.theirs !== undefined
      ? matrix[option.ours][option.theirs]
      : null;

  return (
    <li className={"option" + (best ? " best" : "")}>
      <button type="button" className="option-main tappable" onClick={onChoose}>
        <span className="option-label">{label}</span>
        <span className={"option-value" + (wins ? " winning" : "")}>{show(shownValue)}</span>
      </button>
      <div className="option-meta">
        {showHints &&
          (best ? (
            <span className="tag">{ownerIsUs ? "best" : "their strongest"}</span>
          ) : !level ? (
            <span className="tag cost">-{show(shownCost)}</span>
          ) : (
            <span className="tag cost">same floor</span>
          ))}
        {concreteRating !== null && (
          <span
            className="pick-rating"
            style={{ background: ratingColor(toFraction(concreteRating, scale)) }}
            title={`Our rating of this matchup: ${points(concreteRating)}`}
          >
            {show(ratingValue(concreteRating))}
          </span>
        )}
        {showProse && profile && <ProfileBar profile={profile} unit={roundUnit} />}
      </div>
      {showHints && decision.kind === "forced" && (
        <p className="pick-hint forced-why">
          No choice here &mdash; {label} is the only legal pairing, so the engine
          plays it and moves on.
          {concreteRating !== null && (
            <> Your grid rates the matchup {show(ratingValue(concreteRating))}.</>
          )}
        </p>
      )}
    </li>
  );
}

/**
 * The two numbers that separate options minimax rates identically: how much is
 * still reachable if they misstep, and how many of their replies take it away.
 *
 * The profile arrives already priced in the currency on show, so both figures
 * come from the same search in the same units; only the reply counts are
 * currency-free.
 */
function ProfileBar({ profile, unit }: { profile: OptionProfile; unit: Unit }) {
  const safe = profile.totalReplies - profile.punishingReplies;
  return (
    <span className="profile">
      <span className={"profile-upside" + (profile.upside > 0 ? " live" : "")}>
        up to {inUnit(unit, profile.ifTheyErr)}
      </span>
      <span className="profile-risk">
        {profile.punishingReplies === 0
          ? "nothing they do lowers it"
          : `${profile.punishingReplies} of ${profile.totalReplies} replies hold you to ${inUnit(unit, profile.guaranteed)}`}
        {safe > 0 && profile.upside > 0 && ` · ${safe} give you more`}
      </span>
    </span>
  );
}

/**
 * The sentence to read when every option shows the same number.
 *
 * Saying "it is a tie" is the app admitting it has run out of things to say.
 * There is almost always signal underneath: the same guaranteed floor can hide
 * twice the upside, or three times the chance of being punished.
 */
function summariseTieBreak(
  ranked: { o: MoveOption; p?: OptionProfile; pShown?: OptionProfile }[],
  unit: Unit,
): { lead: string; body: string } | null {
  const entries = ranked.filter(
    (x): x is { o: MoveOption; p: OptionProfile; pShown: OptionProfile } =>
      !!x.p && !!x.pShown,
  );
  if (entries.length < 2) return null;

  const best = entries[0].o.value;
  const tied = entries.filter((x) => Math.abs(x.o.value - best) < 1e-9);
  if (tied.length < 2) return null;

  // Judged on the points profile, so which of the two paragraphs appears is
  // decided by the engine and not by a display setting. Only the figures
  // inside them follow the unit.
  const upsides = new Set(tied.map((x) => x.p.upside.toFixed(3)));
  const risks = new Set(tied.map((x) => x.p.punishingReplies));

  // The options tie exactly on the points floor -- that is what put them here.
  // They need not tie in chance, so the claim they all support is the weakest
  // of them, and "at least" is the wording that stays true in both currencies.
  const floor =
    unit === "chance" ? Math.min(...tied.map((x) => x.pShown.guaranteed)) : best;
  const floorText = inUnit(unit, floor);
  const holds = unit === "chance" ? `at least ${floorText}` : floorText;

  if (upsides.size === 1 && risks.size === 1) {
    return {
      lead: `${tied.length} options all guarantee ${holds}.`,
      body:
        "They are genuinely equivalent -- same upside, same exposure. Nothing " +
        "in the numbers separates them, so pick on what the numbers do not " +
        "know: terrain, who wants the table, who is playing well today.",
    };
  }

  const top = tied[0].pShown;
  return {
    lead: `${tied.length} options all guarantee ${holds} -- but they are not equal.`,
    body:
      `The one at the top reaches ${inUnit(unit, top.ifTheyErr)} if they misstep, and only ` +
      `${top.punishingReplies} of their ${top.totalReplies} replies holds you to ` +
      `${floorText}. The others give up upside, or hand them more ways to punish you, ` +
      `for exactly the same floor.`,
  };
}

/**
 * Hold or play, per player.
 *
 * This is the question a ranking cannot answer: not "who has the best matchup"
 * but "whose good matchups still exist three decisions from now". A player with
 * a positive number here has opportunities later that do not exist yet.
 */
function Leverage({
  leverage,
  unit,
  ourName,
}: {
  leverage: ReturnType<typeof playerLeverage>;
  /** The currency `leverage` was priced in, and so the one it prints in. */
  unit: Unit;
  ourName: (i: number) => string;
}) {
  const spread =
    leverage[0].gainFromWaiting - leverage[leverage.length - 1].gainFromWaiting;

  // Measured across all 31 WTC 2024 boards: at the opening the players separate
  // on only 15 of them, median spread 0.00. One decision later it is 26 of 31,
  // median 2.00. So a flat readout here is the common case, not a failure -- and
  // silently hiding the panel taught the user nothing about why it comes and
  // goes. Saying "nothing in it, and here is when it will matter" is a usable
  // signal; an empty space is not. See docs/WTC2024_GROUND_TRUTH.md Finding 15.
  if (spread <= 0) {
    return (
      <div className="leverage flat">
        <h3>Hold or play</h3>
        <p className="leverage-lead">
          Nothing in it. Every player is worth the same to hold, so this pick
          costs you nothing either way — lead with whoever you like. Your{" "}
          <strong>next</strong> decision, once they have answered, is where
          holding usually starts to matter.
        </p>
      </div>
    );
  }

  const hold = leverage[0];
  const now = leverage[leverage.length - 1];

  return (
    <div className="leverage">
      <h3>Hold or play</h3>
      <p className="leverage-lead">
        Holding <strong>{ourName(hold.player)}</strong> is worth{" "}
        {gapInUnit(unit, hold.gainFromWaiting)} more than committing them here.{" "}
        <strong>{ourName(now.player)}</strong> is the opposite — their moment is
        this one, by {gapInUnit(unit, now.gainFromWaiting)}.
      </p>
      <ul>
        {leverage.map((l) => (
          <li key={l.player}>
            <span>{ourName(l.player)}</span>
            <span
              className={
                "gain " + (l.gainFromWaiting > 0 ? "up" : l.gainFromWaiting < 0 ? "down" : "flat")
              }
            >
              {l.gainFromWaiting > 0 ? "+" : l.gainFromWaiting < 0 ? "-" : ""}
              {gapInUnit(unit, l.gainFromWaiting)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Result({
  state,
  chance,
  scale,
  unit,
  ourName,
  theirName,
}: {
  state: LiveState;
  /** The round-win chance of the completed board, in [0, 1]. */
  chance: number;
  scale: Scale;
  unit: Unit;
  ourName: (i: number) => string;
  theirName: (i: number) => string;
}) {
  // Won or lost is always the chance question, whichever currency is on show:
  // the round is taken or it is not, and a points total does not say which.
  const won = chance > 0.5;
  const rating = (v: number) =>
    inUnit(unit, unit === "chance" ? toWinProbability(v, scale.min, scale.max) : v);
  return (
    <div className={"result " + (won ? "won" : "lost")}>
      <p className="result-score">{inUnit(unit, unit === "chance" ? chance : state.banked)}</p>
      <p className="result-note">
        {won ? "Takes the round" : "Falls short of the round"}
      </p>
      <ul className="result-tables">
        {state.committed.map((c, i) => (
          <li key={i}>
            {ourName(c.ours)} vs {theirName(c.theirs)}
            {c.table && <span className="table-tag"> — Table {c.table}</span>} — {rating(c.value)}
          </li>
        ))}
      </ul>
    </div>
  );
}
