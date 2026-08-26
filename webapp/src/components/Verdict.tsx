import { useMemo, useState } from "react";
import { worstMatchupDodge } from "../engine/avoidance";
import type { Matrix } from "../engine/boardAnalysis";
import { decisionReport, evenThreshold, LIVE, SECURED, UNWINNABLE } from "../engine/boardAnalysis";
import { outlook } from "../engine/opponent";
import { protocolFloor } from "../engine/protocol";
import { reachReport } from "../engine/reach";
import type { Board } from "../model/board";
import { boardMatrix, boardScale, isRated } from "../model/board";
import type { DodgeMode } from "../model/settings";

interface Props {
  board: Board;
  onHighlight?: (cells: Set<string>) => void;
  /** How much to say about the worst matchup. Defaults to asking first. */
  dodgeMode?: DodgeMode;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/** "A", "A and B", "A, B and C" -- never a trailing comma before "and". */
const listNames = (names: string[]): string =>
  names.length <= 1
    ? (names[0] ?? "")
    : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;


/** Probabilities are shown as whole rounds per hundred, never as raw decimals. */
const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

/**
 * What the round is actually worth.
 *
 * Four numbers matter and the desktop app shows none of them plainly:
 *
 *  - the guaranteed total, which is what we hold if they hunt us perfectly
 *  - the typical total, which is what happens when they play their own board
 *  - the ceiling, which is the best still reachable
 *  - the threshold, which is the line between winning the round and not
 *
 * The first two are the must-not-lose and must-win readings of the same
 * position, and they are frequently more than a point apart. Showing only
 * the guaranteed number -- as this screen used to -- silently hands every
 * decision to the pessimistic one. See Finding 16 in
 * docs/WTC2024_GROUND_TRUTH.md.
 *
 * Everything else on this screen exists to answer "so what do I do", and is
 * driven by the measured findings rather than by a single ranking number.
 */
export function Verdict({ board, onHighlight, dodgeMode = "onDemand" }: Props) {
  const scale = boardScale(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);

  const report = useMemo(() => decisionReport(matrix, tau), [matrix, tau]);
  const pWe = useMemo(() => protocolFloor(matrix, true).value, [matrix]);
  const pThey = useMemo(() => protocolFloor(matrix, false).value, [matrix]);

  const o = report.board;
  const guaranteed = board.ourTeamFirst ? pWe : pThey;
  const initiative = pWe - pThey;

  // What happens when they optimise their own board rather than hunting ours.
  // Finding 16: the guaranteed number is 1.40 pts pessimistic on real data,
  // because it credits them with a grid that is the exact negative of ours --
  // and two real teams' grids correlate at r = -0.049, not -1.
  const typical = useMemo(
    () =>
      outlook(
        matrix,
        {
          ourPool: (1 << matrix.length) - 1,
          theirPool: (1 << matrix.length) - 1,
          attacker: -1,
          attackerSide: board.ourTeamFirst ? "our" : "their",
        },
        guaranteed,
      ),
    [matrix, board.ourTeamFirst, guaranteed],
  );

  // The matchup on this board we would least like to play, and whether the
  // pairing protocol actually lets us refuse it.
  //
  // Priced in round-win probability, not points. The points-valued twin of this
  // read 0.000 on all 31 saved boards, because a points total barely moves when
  // you swap which bad cell you eat -- the total is nearly the same either way.
  // The round does not care about the total; it cares whether three games fall
  // your way. Under that currency the worst cell is worth 8.2% on average and
  // 15.9% at the extreme.
  //
  // Deliberately narrow: only the worst-rated matchup, only when it is actually
  // bad, and silent otherwise. A list of 25 priced dodges is noise on a phone.
  //
  // It is not shown unconditionally, because measurement says it would never
  // stop showing: on all 31 saved boards there is a matchup below the midpoint,
  // so this insight has something to say every single time. `asked` gates both
  // the display AND the solve -- in "off" and "onDemand" the engine is not run
  // at all, so the cost is genuinely not paid rather than paid invisibly.
  const [asked, setAsked] = useState(false);
  const wantDodge = dodgeMode === "always" || (dodgeMode === "onDemand" && asked);

  const worstDodge = useMemo(
    () =>
      wantDodge ? worstMatchupDodge(matrix, scale.min, scale.max, board.ourTeamFirst) : null,
    [wantDodge, matrix, scale.min, scale.max, board.ourTeamFirst],
  );

  /*
    Who the protocol puts out of reach.
    
    Unconditional, unlike the dodge price, because it is ten sorts of five
    numbers -- 0.008 ms per board -- rather than a search. There is nothing to
    gate.

    Measured on the 31 saved boards, the two halves earn very different
    treatment, which is why only one of them is always on screen:

      players who cannot be forced into their own worst matchup
        per board 0:2  1:6  2:12  3:10  4:1  5:0, mean 2.06 of 5
        silent on 2/31 boards

      their columns that read better than they play
        per board 0:15  1:8  2:7  3:1, mean 0.81 of 5
        silent on 15/31 boards

    The first is a sentence about two of your five players on nearly every
    board, and it changes what you spend nominations on. The second is absent
    from half of them, so it appears only when it has something to say rather
    than holding a permanent slot to say nothing.
  */
  const reach = useMemo(
    () => reachReport(matrix, undefined, board.ourTeamFirst),
    [matrix, board.ourTeamFirst],
  );

  const shielded = reach.floors.filter((f) => f.protectedByProtocol);
  const overstated = reach.ceilings.filter((c) => c.overstated);

  // Rosters are frequently half-typed, so a blank name has to degrade into
  // something you can still find on the grid rather than an empty gap in a
  // sentence.
  const ourName = (i: number) => board.ourPlayers[i]?.trim() || `Your player ${i + 1}`;
  const theirName = (i: number) => board.theirPlayers[i]?.trim() || `Their list ${i + 1}`;

  // An all-even board is arithmetically "unwinnable" -- it lands exactly on the
  // threshold, which needs to be beaten rather than met. Saying so before a
  // single matchup has been rated is technically true and completely useless.
  if (!isRated(board)) {
    return (
      <section className="verdict">
        <div className="chip live">Not rated yet</div>
        <p className="reading">
          Every matchup is sitting on dead even, so there is nothing to read yet.
          Tap a cell to rate it. The numbers here update as you go.
        </p>
      </section>
    );
  }

  const verdictLabel =
    o.verdict === UNWINNABLE
      ? "Cannot be won"
      : o.verdict === SECURED
        ? "Already won"
        : "Live";

  const dominant =
    report.frontier.length === 1 && !report.choiceMatters ? report.frontier[0] : null;

  return (
    <section className="verdict">
      <div className={`chip ${o.verdict}`}>{verdictLabel}</div>

      <div className="numbers">
        <Stat
          label="Guaranteed"
          value={fmt(guaranteed)}
          note="if they hunt you perfectly"
          strong
        />
        <Stat
          label="Typical"
          value={fmt(typical.expected)}
          note="if they play their own board"
          strong
        />
        <Stat label="Ceiling" value={fmt(o.ceiling)} note="best still reachable" />
      </div>

      <p className="reading">
        {o.verdict === UNWINNABLE ? (
          <>
            Every remaining pairing loses this round. The ceiling is {fmt(o.ceiling)} and
            the round needs more than {fmt(tau)}. Play for the points you can still bank,
            not for the win.
          </>
        ) : o.verdict === SECURED ? (
          <>
            The round is already won at {fmt(o.floor)}, whatever they do next. Anything
            further is bonus.
          </>
        ) : guaranteed > tau ? (
          <>
            Playing this out properly guarantees {fmt(guaranteed)}, which takes the round
            outright. It cannot be taken away from you.
          </>
        ) : typical.expected > tau ? (
          <>
            The safe reading is {fmt(guaranteed)}
            {tau - guaranteed < 0.05
              ? ` -- dead level with the round, and level does not win it -- `
              : ` -- ${fmt(tau - guaranteed)} short of the round -- `}
            but that credits them with knowing exactly which matchups hurt you most.
            Playing their own board they land you nearer {fmt(typical.expected)}, which
            wins it. This is a round you take by playing for the win, not by protecting
            the floor.
          </>
        ) : (
          <>
            Guaranteed {fmt(guaranteed)}, typically {fmt(typical.expected)}, and the round
            needs {fmt(tau)}. Neither reading gets there on its own, so the win has to come
            from the ceiling at {fmt(o.ceiling)} -- it needs them to give you something.
          </>
        )}
      </p>

      <div className="insight-list">
        {/*
          The permutation floor counts outcomes the pairing protocol can never
          actually produce, so it reads more pessimistic than the real game.
        */}
        {guaranteed > o.floor && (
          <Insight
            title={`The protocol protects ${fmt(guaranteed - o.floor)} of that`}
            body={`A naive worst case says ${fmt(o.floor)}, but that assumes they can hand-pick any
              set of matchups. They cannot -- pairing is turn-taking, and half the decisions
              are yours. Against best play you hold ${fmt(guaranteed)}.`}
          />
        )}

        {typical.expected - guaranteed >= 0.5 && (
          <Insight
            title={`Being hunted costs ${fmt(typical.expected - guaranteed)} of that`}
            body={`The guaranteed ${fmt(guaranteed)} assumes their grid is the exact opposite of
              yours -- every matchup you rated good, they rated bad. Two real WTC teams'
              grids matched that shape almost not at all. Playing a board of their own they
              land you nearer ${fmt(typical.expected)}, and rarely below ${fmt(typical.low)}.
              Use ${fmt(guaranteed)} when you must not lose, ${fmt(typical.expected)} when
              you must win.`}
          />
        )}

        {initiative !== 0 ? (
          <Insight
            title={
              initiative < 0
                ? `Going first costs ${fmt(-initiative)}`
                : `Going first gains ${fmt(initiative)}`
            }
            body={
              initiative < 0
                ? `Guaranteed ${fmt(pWe)} if you put a player up first, ${fmt(pThey)} if they do.
                   The side that offers the pair controls the menu; the side that picks only
                   chooses from it. If the order is yours to influence, make them commit first.`
                : `Guaranteed ${fmt(pWe)} opening, ${fmt(pThey)} if they open. Unusually, this
                   board rewards committing first.`
            }
          />
        ) : (
          /*
            The dice-off is free on this board, and saying nothing about that is
            not the same as saying so. Silence here reads as "not calculated",
            which is the one thing it never is -- `initiative` exists on every
            render from two protocolFloor calls the panel already makes.

            Measured over the 31 saved event boards the gap takes exactly one
            non-zero value, 1.000 points, and is exactly zero on 13 of them. So
            this branch fires on more than a third of real boards, and on those
            boards losing the roll costs nothing at all. That is worth a line:
            it frees you from spending any thought on an outcome you cannot
            control.

            Deliberately phrased in points and not in round-win chance. The
            probability version of this gap is also a single constant, 7.96875
            percentage points, and it costs 17-36 ms of winChanceFloor to
            recover a number that carries no board-specific information.
          */
          <Insight
            title="The dice-off does not matter here"
            body={`Guaranteed ${fmt(pWe)} either way -- ${fmt(pWe)} if you put a player up first,
                   ${fmt(pThey)} if they do. Win or lose the roll, this board hands you the same
                   floor, so there is nothing to plan around and nothing to regret.`}
          />
        )}

        {/*
          Offered rather than shown. One tap, and it stays open for this board.
        */}
        {dodgeMode === "onDemand" && !asked && (
          <button className="ghost wide" onClick={() => setAsked(true)}>
            Price your worst matchup
          </button>
        )}

        {wantDodge && worstDodge === null && (
          <p className="hint">
            Nothing on this board is rated badly enough to be worth dodging.
          </p>
        )}

        {worstDodge && (
          <Insight
            title={
              worstDodge.cheapest === null
                ? `You cannot avoid ${board.ourPlayers[worstDodge.example.ours]} into ${board.theirPlayers[worstDodge.example.theirs]}`
                : worstDodge.cheapest.free
                  ? `Your worst matchup is free to refuse`
                  : `Refusing your worst matchup costs ${pct(worstDodge.cheapest.price ?? 0)}`
            }
            body={
              worstDodge.cheapest === null
                ? `Rated ${fmt(worstDodge.rating)}, and no line of play escapes it -- they can force
                   it whatever you do. Plan the other four around eating this one rather than
                   spending decisions trying to dodge what cannot be dodged.`
                : worstDodge.cheapest.free
                  ? `${board.ourPlayers[worstDodge.cheapest.cell.ours]} into
                     ${board.theirPlayers[worstDodge.cheapest.cell.theirs]} is rated
                     ${fmt(worstDodge.rating)}, and refusing it costs nothing measurable -- your
                     chance of taking the round is the same either way. Take the dodge.`
                  : `${board.ourPlayers[worstDodge.cheapest.cell.ours]} into
                     ${board.theirPlayers[worstDodge.cheapest.cell.theirs]} is rated
                     ${fmt(worstDodge.rating)}. Staying out of it drops your chance of taking the
                     round from ${pct(worstDodge.cheapest.base)} to
                     ${pct(worstDodge.cheapest.avoided ?? 0)}. That is the price of the dodge --
                     worth paying only if you think the rating understates how bad it is.`
            }
            onFocus={() => {
              const c = worstDodge.cheapest ? worstDodge.cheapest.cell : worstDodge.example;
              onHighlight?.(new Set([`${c.ours}-${c.theirs}`]));
            }}
          />
        )}

        {dominant && (
          <Insight
            title={`${board.ourPlayers[dominant.ours]} into ${board.theirPlayers[dominant.theirs]} costs nothing`}
            body={`It protects the floor without giving up any ceiling -- there is no trade-off
              to weigh. A metric that only ranks by expected value rates it the same as
              pairings that are strictly worse.`}
            onFocus={() => onHighlight?.(new Set([`${dominant.ours}-${dominant.theirs}`]))}
          />
        )}

        {shielded.length > 0 && (
          <Insight
            title={
              shielded.length === 1
                ? `${ourName(shielded[0].ours)} cannot be forced into their worst matchup`
                : `${listNames(shielded.map((f) => ourName(f.ours)))} cannot be forced into their worst matchups`
            }
            body={
              shielded.length === 1
                ? `Their worst cell is rated ${fmt(shielded[0].rowWorst)} and it is the only
                   ${fmt(shielded[0].rowWorst)} in that row -- a single matchup, and a single
                   matchup can always be refused. The worst they can actually be held to is
                   ${fmt(shielded[0].level)}. Spending a nomination to protect them buys
                   nothing.`
                : `Each of their worst cells is the only one of its rating in that row, and a
                   lone matchup can always be refused. Their real floors are better than the
                   grid reads. Spend nominations on the players whose bad matchup is repeated
                   -- those are the ones that can genuinely be forced.`
            }
            onFocus={() =>
              onHighlight?.(
                new Set(shielded.flatMap((f) => f.via.map((t) => `${f.ours}-${t}`))),
              )
            }
          />
        )}

        {overstated.length > 0 && (
          <Insight
            title={
              overstated.length === 1
                ? `${theirName(overstated[0].theirs)} reads better than they play`
                : `${listNames(overstated.map((c) => theirName(c.theirs)))} read better than they play`
            }
            body={
              overstated.length === 1
                ? `Your best cell against them is rated ${fmt(overstated[0].columnBest)}, but it is
                   the only ${fmt(overstated[0].columnBest)} in that column, so they can refuse it
                   and you cannot insist. ${overstated[0].level === null ? "" : `Hold them to ${fmt(overstated[0].level)} instead.`}
                   Do not build a plan around a matchup you cannot force.`
                : `In each of those columns your best cell is a lone one, which they can refuse.
                   The grid promises matchups you have no way to insist on, so treat those
                   columns as worse than they look.`
            }
            onFocus={() =>
              onHighlight?.(
                new Set(overstated.flatMap((c) => c.via.map((o) => `${o}-${c.theirs}`))),
              )
            }
          />
        )}

        {report.choiceMatters && (
          <Insight
            title={`A real trade-off: ${fmt(report.floorAtStake)} floor against ${fmt(report.ceilingAtStake)} ceiling`}
            body={`Safest is ${board.ourPlayers[report.safest.ours]} into
              ${board.theirPlayers[report.safest.theirs]} (floor ${fmt(report.safest.outlook.floor)}).
              Boldest is ${board.ourPlayers[report.boldest.ours]} into
              ${board.theirPlayers[report.boldest.theirs]} (ceiling ${fmt(report.boldest.outlook.ceiling)}).
              This is the one call the app should not make for you: take the floor if you
              must not lose, take the ceiling if you must win.`}
            onFocus={() =>
              onHighlight?.(
                new Set([
                  `${report.safest.ours}-${report.safest.theirs}`,
                  `${report.boldest.ours}-${report.boldest.theirs}`,
                ]),
              )
            }
          />
        )}

        {report.hiddenFloorCost > 0 && (
          <Insight
            title={`${fmt(report.hiddenFloorCost)} points hide behind a tie`}
            body={`Several pairings reach the same ceiling, so a single score rates them
              equally. Their guaranteed floors differ by ${fmt(report.hiddenFloorCost)}.
              Picking the wrong one of two "equal" options gives that away for nothing.`}
          />
        )}
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  note,
  strong,
}: {
  label: string;
  value: string;
  note?: string;
  strong?: boolean;
}) {
  return (
    <div className={"stat" + (strong ? " strong" : "")}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {note ? <span className="stat-note">{note}</span> : null}
    </div>
  );
}

function Insight({
  title,
  body,
  onFocus,
}: {
  title: string;
  body: string;
  onFocus?: () => void;
}) {
  return (
    <div className="insight" onClick={onFocus} role={onFocus ? "button" : undefined}>
      <p className="insight-title">{title}</p>
      <p className="insight-body">{body}</p>
    </div>
  );
}

export { LIVE };
