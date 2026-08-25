import { useMemo } from "react";
import type { Matrix } from "../engine/boardAnalysis";
import { evenThreshold } from "../engine/boardAnalysis";
import type { LiveState, MoveOption, OptionProfile } from "../engine/live";
import {
  commitPairing,
  currentDecision,
  moveOptions,
  optionProfile,
  playerLeverage,
} from "../engine/live";
import type { Board } from "../model/board";
import { boardMatrix, boardScale } from "../model/board";

interface Props {
  board: Board;
  state: LiveState;
  onState: (s: LiveState) => void;
  onReset: () => void;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

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
export function LivePanel({ board, state, onState, onReset }: Props) {
  const scale = boardScale(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);

  const decision = useMemo(() => currentDecision(state), [state]);
  const rawOptions = useMemo(() => moveOptions(matrix, state), [matrix, state]);
  const leverage = useMemo(() => playerLeverage(matrix, state), [matrix, state]);

  /*
   * When several of our options carry the same guaranteed value, minimax has
   * nothing left to say and the app would otherwise present a coin flip. The
   * profile looks at the same options across every reply they have, which
   * separates them on 24 of the 28 real 2024 boards where the top openers tie.
   *
   * Options are then ranked by guaranteed value first -- never trade the floor
   * away -- and only among equals by upside, then by how few replies punish it.
   */
  const ranked = useMemo(() => {
    const ours = "owner" in decision && decision.owner === "our";
    const plain = rawOptions.map((o) => ({ o, p: undefined as OptionProfile | undefined }));
    if (!ours || rawOptions.length < 2) return plain;

    const best = rawOptions[0].value;
    const tiedCount = rawOptions.filter((o) => Math.abs(o.value - best) < 1e-9).length;
    if (tiedCount < 2) return plain;

    const withProfiles = rawOptions.map((o) => ({
      o,
      p: optionProfile(matrix, state, o) ?? undefined,
    }));

    withProfiles.sort(
      (a, b) =>
        b.o.value - a.o.value ||
        (b.p?.upside ?? 0) - (a.p?.upside ?? 0) ||
        (a.p?.punishingReplies ?? 0) - (b.p?.punishingReplies ?? 0),
    );
    return withProfiles;
  }, [matrix, state, rawOptions, decision]);

  const tieBreak = useMemo(() => summariseTieBreak(ranked), [ranked]);

  const ourName = (i: number) => board.ourPlayers[i] ?? `Us ${i + 1}`;
  const theirName = (i: number) => board.theirPlayers[i] ?? `Them ${i + 1}`;

  const ownerIsUs = "owner" in decision && decision.owner === "our";

  function applyOpen(playerIndex: number, owner: "our" | "their") {
    onState({
      ...state,
      ourPool: owner === "our" ? state.ourPool & ~(1 << playerIndex) : state.ourPool,
      theirPool: owner === "their" ? state.theirPool & ~(1 << playerIndex) : state.theirPool,
      attacker: playerIndex,
      attackerSide: owner,
    });
  }

  /** Record which of an offered pair was taken. */
  function applyPick(pair: [number, number], picked: number) {
    const leftover = picked === pair[0] ? pair[1] : pair[0];
    const attackerIsUs = state.attackerSide === "our";
    const [ours, theirs] = attackerIsUs
      ? [state.attacker, picked]
      : [picked, state.attacker];
    onState(commitPairing(matrix, state, ours, theirs, leftover, attackerIsUs ? "their" : "our"));
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
          {tieBreak && (
            <div className="tiebreak">
              <p className="tiebreak-lead">{tieBreak.lead}</p>
              <p className="tiebreak-body">{tieBreak.body}</p>
            </div>
          )}

          <ol className="options">
            {ranked.map(({ o, p }, idx) => (
              <OptionRow
                key={idx}
                option={o}
                profile={p}
                decision={decision}
                best={idx === 0}
                ownerIsUs={ownerIsUs}
                tau={tau}
                ourName={ourName}
                theirName={theirName}
                onChoose={() => {
                  if (decision.kind === "open") {
                    applyOpen(
                      decision.owner === "our" ? o.ours! : o.theirs!,
                      decision.owner,
                    );
                  } else if (decision.kind === "forced") {
                    onState(commitPairing(matrix, state, o.ours!, o.theirs!, null, null));
                  }
                }}
                onPick={(picked) => applyPick(o.pair!, picked)}
              />
            ))}
          </ol>

          {leverage.length > 1 && <Leverage leverage={leverage} ourName={ourName} />}
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
  best,
  ownerIsUs,
  tau,
  ourName,
  theirName,
  onChoose,
  onPick,
}: {
  option: MoveOption;
  profile?: OptionProfile;
  decision: ReturnType<typeof currentDecision>;
  best: boolean;
  ownerIsUs: boolean;
  tau: number;
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
    return (
      <li className={"option" + (best ? " best" : "")}>
        <div className="option-main">
          <span className="option-label">
            {names(option.pair[0])} or {names(option.pair[1])}
          </span>
          <span className={"option-value" + (wins ? " winning" : "")}>{fmt(option.value)}</span>
        </div>
        <div className="option-meta">
          {best ? (
            <span className="tag">
              {ownerIsUs ? "best offer" : "their strongest"}
            </span>
          ) : cost > 1e-9 ? (
            <span className="tag cost">-{fmt(cost)}</span>
          ) : (
            <span className="tag cost">same floor</span>
          )}
        </div>
        <div className="pick-row">
          {option.pair.map((p) => (
            <button key={p} type="button" className="pick" onClick={() => onPick(p)}>
              {names(p)} played
            </button>
          ))}
        </div>
      </li>
    );
  }

  const label =
    option.ours !== undefined && option.theirs !== undefined
      ? `${ourName(option.ours)} vs ${theirName(option.theirs)}`
      : option.ours !== undefined
        ? ourName(option.ours)
        : theirName(option.theirs!);

  return (
    <li className={"option" + (best ? " best" : "")}>
      <button type="button" className="option-main tappable" onClick={onChoose}>
        <span className="option-label">{label}</span>
        <span className={"option-value" + (wins ? " winning" : "")}>{fmt(option.value)}</span>
      </button>
      <div className="option-meta">
        {best ? (
          <span className="tag">{ownerIsUs ? "best" : "their strongest"}</span>
        ) : cost > 1e-9 ? (
          <span className="tag cost">-{fmt(cost)}</span>
        ) : (
          <span className="tag cost">same floor</span>
        )}
        {profile && <ProfileBar profile={profile} />}
      </div>
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
  if (spread <= 0) return null;

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
