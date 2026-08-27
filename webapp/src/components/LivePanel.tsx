import { useMemo, useState } from "react";
import type { Matrix } from "../engine/boardAnalysis";
import { evenThreshold } from "../engine/boardAnalysis";
import type { LiveState, MoveOption, OptionProfile, PickOption } from "../engine/live";
import {
  commitPairing,
  currentDecision,
  liveWinChance,
  moveOptions,
  optionProfile,
  pickOptions,
  pickTieBreak,
  playerLeverage,
} from "../engine/live";
import { solveCache, type SolveCache } from "../engine/protocol";
import type { Board } from "../model/board";
import { boardMatrix, boardScale } from "../model/board";
import { pct } from "../model/format";
import { ratingColor, toFraction, type Scale } from "../model/scale";
import type { AdviceLevel, SurpriseMode } from "../model/settings";

interface Props {
  board: Board;
  state: LiveState;
  onState: (s: LiveState) => void;
  onReset: () => void;
  /**
   * How much the round explains itself. Defaults to full: the engine does the
   * same search either way, so a caller that never sets this gets every "why"
   * exactly as before, which is what the live-round tests rely on.
   */
  adviceLevel?: AdviceLevel;
  surpriseMode?: SurpriseMode;
  surpriseRegretThreshold?: number;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

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
  adviceLevel = "full",
  surpriseMode = "off",
  surpriseRegretThreshold = 0,
}: Props) {
  const scale = boardScale(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);

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

  const rawOptions = useMemo(() => moveOptions(matrix, state, cache), [matrix, state, cache]);
  const leverage = useMemo(() => playerLeverage(matrix, state, cache), [matrix, state, cache]);

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

  const tieBreak = useMemo(() => summariseTieBreak(ranked), [ranked]);

  const ourName = (i: number) => board.ourPlayers[i] ?? `Us ${i + 1}`;
  const theirName = (i: number) => board.theirPlayers[i] ?? `Them ${i + 1}`;

  const ownerIsUs = "owner" in decision && decision.owner === "our";
  const [surprise, setSurprise] = useState<SurpriseNotice | null>(null);

  const surpriseEnabled = surpriseMode === "on";
  const surpriseThreshold = Math.max(0, surpriseRegretThreshold);

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
    onState(next);
  }

  return (
    <section className="live">
      <header className="live-head">
        <div>
          <h2>{prompt(decision, ourName, theirName)}</h2>
          <p className="live-sub">
            {state.committed.length} of {board.ourPlayers.length} tables set
            {state.committed.length > 0 && <> &middot; {fmt(state.banked)} banked</>}
            {" "}&middot; {fmt(tau)} takes the round
          </p>
        </div>
        <button type="button" className="ghost" onClick={onReset}>
          Restart
        </button>
      </header>

      {decision.kind === "done" ? (
        <Result state={state} tau={tau} ourName={ourName} theirName={theirName} />
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
                They gave up {fmt(surprise.regret)} points against your model ({fmt(surprise.valueDelta)} to
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
            {ranked.map(({ o, p }, idx) => (
              <OptionRow
                key={idx}
                option={o}
                profile={p}
                decision={decision}
                matrix={matrix}
                state={state}
                cache={cache}
                best={idx === 0}
                ownerIsUs={ownerIsUs}
                tau={tau}
                ratingSpan={scale.max - scale.min}
                scale={scale}
                showProse={showProse}
                showHints={showHints}
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
                    onState(commitPairing(matrix, state, o.ours!, o.theirs!, null, null));
                  }
                }}
                onPick={(picked) => applyPick(o.pair!, picked, o)}
              />
            ))}
          </ol>

          {showProse && leverage.length > 1 && (
            <Leverage leverage={leverage} ourName={ourName} />
          )}
        </>
      )}

      {state.committed.length > 0 && (
        <div className="committed">
          <h3>Tables set</h3>
          <ul>
            {state.committed.map((c, i) => (
              <li key={i}>
                <span>
                  {ourName(c.ours)} vs {theirName(c.theirs)}
                </span>
                <strong>{fmt(c.value)}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
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
  tau,
  ratingSpan,
  scale,
  showProse,
  showHints,
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
  tau: number;
  /** `scale.max - scale.min`; the tie-break threshold is a fraction of it. */
  ratingSpan: number;
  /** The board scale, for colouring raw matchup-rating chips on each tile. */
  scale: Scale;
  /** Show the explanatory paragraphs (full only). */
  showProse: boolean;
  /** Show the one-line recommendation and the tags (full and brief). */
  showHints: boolean;
  ourName: (i: number) => string;
  theirName: (i: number) => string;
  onChoose: () => void;
  onPick: (picked: number) => void;
}) {
  const wins = option.value > tau;
  const cost = Math.abs(option.regret);

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
    return (
      <li className={"option" + (best ? " best" : "")}>
        <div className="option-main">
          <span className="option-label">
            {names(option.pair[0])} or {names(option.pair[1])}
          </span>
          <span className={"option-value" + (wins ? " winning" : "")}>{fmt(option.value)}</span>
        </div>
        <div className="option-meta">
          {showHints &&
            (best ? (
              <span className="tag">
                {ownerIsUs ? "best offer" : "their strongest"}
              </span>
            ) : cost > 1e-9 ? (
              <span className="tag cost">-{fmt(cost)}</span>
            ) : (
              <span className="tag cost">same floor</span>
            ))}
        </div>
        <div className="pick-row">
          {picks.map((p) => (
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
                style={{ background: ratingColor(toFraction(ratingFor(p.player), scale)) }}
                title={choiceIsOurs ? "Our rating of this matchup" : "Their rating of this matchup"}
              >
                {fmt(ratingFor(p.player))}
              </span>
              <span className={"pick-value" + (p.value > tau ? " winning" : "")}>
                {fmt(p.value)}
              </span>
            </button>
          ))}
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
                Both hold {fmt(picks[0].value)}, and your grid rates{" "}
                {names(tieBreak.player)} and {names(tieBreak.other)} the same
                against everyone you have left &mdash; so this is genuinely
                yours to call. Pick on what the sheet cannot see: terrain, who
                wants the table, who is on form.
              </>
            ) : tieBreak ? (
              <>
                Both hold {fmt(picks[0].value)}. Take{" "}
                <strong>{names(tieBreak.player)}</strong> &mdash;{" "}
                {tieBreak.reason === "typical" ? (
                  <>
                    if they play their own board it leaves {fmt(tieBreak.value)}{" "}
                    reachable against {fmt(tieBreak.otherValue)}.
                  </>
                ) : tieBreak.reason === "upside" ? (
                  <>
                    same floor either way, but it keeps {fmt(tieBreak.value)} alive
                    if they misplay against {fmt(tieBreak.otherValue)}. Play to
                    your outs.
                  </>
                ) : tieBreak.reason === "average" ? (
                  <>
                    floor, ceiling and pressure all match, but across their whole
                    reply space it averages {fmt(tieBreak.value)} against{" "}
                    {fmt(tieBreak.otherValue)}.
                  </>
                ) : (
                  <>
                    same floor and same upside, but only{" "}
                    {Math.round(tieBreak.value * 100)}% of their replies hold you
                    there, against {Math.round(tieBreak.otherValue * 100)}%.
                  </>
                )}
              </>
            ) : (
              <>
                Both hold {fmt(picks[0].value)} and every measure this app has
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
        <span className={"option-value" + (wins ? " winning" : "")}>{fmt(option.value)}</span>
      </button>
      <div className="option-meta">
        {showHints &&
          (best ? (
            <span className="tag">{ownerIsUs ? "best" : "their strongest"}</span>
          ) : cost > 1e-9 ? (
            <span className="tag cost">-{fmt(cost)}</span>
          ) : (
            <span className="tag cost">same floor</span>
          ))}
        {concreteRating !== null && (
          <span
            className="pick-rating"
            style={{ background: ratingColor(toFraction(concreteRating, scale)) }}
            title="Our rating of this matchup"
          >
            {fmt(concreteRating)}
          </span>
        )}
        {showProse && profile && <ProfileBar profile={profile} />}
      </div>
      {showHints && decision.kind === "forced" && (
        <p className="pick-hint forced-why">
          No choice here &mdash; {label} is the only legal pairing, so the engine
          plays it and moves on.
          {concreteRating !== null && (
            <> Your grid rates the matchup {fmt(concreteRating)}.</>
          )}
        </p>
      )}
    </li>
  );
}

/**
 * The two numbers that separate options minimax rates identically: how much is
 * still reachable if they misstep, and how many of their replies take it away.
 */
function ProfileBar({ profile }: { profile: OptionProfile }) {
  const safe = profile.totalReplies - profile.punishingReplies;
  return (
    <span className="profile">
      <span className={"profile-upside" + (profile.upside > 0 ? " live" : "")}>
        up to {fmt(profile.ifTheyErr)}
      </span>
      <span className="profile-risk">
        {profile.punishingReplies === 0
          ? "nothing they do lowers it"
          : `${profile.punishingReplies} of ${profile.totalReplies} replies hold you to ${fmt(profile.guaranteed)}`}
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
  ranked: { o: MoveOption; p?: OptionProfile }[],
): { lead: string; body: string } | null {
  const entries = ranked.filter(
    (x): x is { o: MoveOption; p: OptionProfile } => !!x.p,
  );
  if (entries.length < 2) return null;

  const best = entries[0].o.value;
  const tied = entries.filter((x) => Math.abs(x.o.value - best) < 1e-9);
  if (tied.length < 2) return null;

  const upsides = new Set(tied.map((x) => x.p.upside.toFixed(3)));
  const risks = new Set(tied.map((x) => x.p.punishingReplies));
  if (upsides.size === 1 && risks.size === 1) {
    return {
      lead: `${tied.length} options all guarantee ${fmt(best)}.`,
      body:
        "They are genuinely equivalent -- same upside, same exposure. Nothing " +
        "in the numbers separates them, so pick on what the numbers do not " +
        "know: terrain, who wants the table, who is playing well today.",
    };
  }

  const top = tied[0].p;
  return {
    lead: `${tied.length} options all guarantee ${fmt(best)} -- but they are not equal.`,
    body:
      `The one at the top reaches ${fmt(top.ifTheyErr)} if they misstep, and only ` +
      `${top.punishingReplies} of their ${top.totalReplies} replies holds you to ` +
      `${fmt(best)}. The others give up upside, or hand them more ways to punish you, ` +
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
  ourName,
}: {
  leverage: ReturnType<typeof playerLeverage>;
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
        {fmt(hold.gainFromWaiting)} more than committing them here.{" "}
        <strong>{ourName(now.player)}</strong> is the opposite — their moment is
        this one, by {fmt(-now.gainFromWaiting)}.
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
              {l.gainFromWaiting > 0 ? "+" : ""}
              {fmt(l.gainFromWaiting)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Result({
  state,
  tau,
  ourName,
  theirName,
}: {
  state: LiveState;
  tau: number;
  ourName: (i: number) => string;
  theirName: (i: number) => string;
}) {
  const won = state.banked > tau;
  return (
    <div className={"result " + (won ? "won" : "lost")}>
      <p className="result-score">{fmt(state.banked)}</p>
      <p className="result-note">
        {won ? "Takes the round" : `Falls ${fmt(tau - state.banked)} short of ${fmt(tau)}`}
      </p>
      <ul className="result-tables">
        {state.committed.map((c, i) => (
          <li key={i}>
            {ourName(c.ours)} vs {theirName(c.theirs)} — {fmt(c.value)}
          </li>
        ))}
      </ul>
    </div>
  );
}
