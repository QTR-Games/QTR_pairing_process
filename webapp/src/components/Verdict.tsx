import { useMemo, useState } from "react";
import { worstMatchupDodge } from "../engine/avoidance";
import type { Matrix } from "../engine/boardAnalysis";
import { decisionReport, evenThreshold, LIVE, SECURED, UNWINNABLE } from "../engine/boardAnalysis";
import { chanceOutlook, outlook } from "../engine/opponent";
import { protocolFloor } from "../engine/protocol";
import { protectionFocus } from "../engine/protection";
import { reachReport } from "../engine/reach";
import { assignmentChanceExtremes, probabilityMatrix, toWinProbability } from "../engine/winProbability";
import type { Board } from "../model/board";
import { boardMatrix, boardScale, isRated } from "../model/board";
import { pct } from "../model/format";
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

/**
 * What the round is actually worth.
 *
 * Three numbers matter, and each is the chance of taking the round rather than
 * a total:
 *
 *  - guaranteed, which is what we hold if they hunt us perfectly
 *  - typical, which is what happens when they play their own board
 *  - the ceiling, which is the best still reachable
 *
 * The first two are the must-not-lose and must-win readings of the same
 * position, and they are frequently a long way apart. Showing only the
 * guaranteed number -- as this screen used to -- silently hands every decision
 * to the pessimistic one. See Finding 16 in docs/WTC2024_GROUND_TRUTH.md.
 *
 * ## Why the threshold is not on this screen
 *
 * There used to be a fourth number: `evenThreshold`, the total a round has to
 * beat. It is a dead constant -- 15 on a 1-5 board and 27.5 on 1-10, for every
 * board, forever -- so a captain reading "the round needs 27.5" was reading a
 * property of the scale rather than a property of the position, and paying a
 * beat at the table to do it.
 *
 * It is gone rather than reformatted. In points the question "does this win the
 * round" is `total > tau`, and `tau` has to be printed for the comparison to
 * parse. In round-win chance the same question is `chance > 50%`, and 50% needs
 * no explaining, so every sentence built around the threshold collapses into a
 * number that is already self-evidently above or below the line.
 *
 * The totals have not been thrown away, because plenty of captains have years
 * of habit in "we're on 15": each box carries its points reading in the note
 * underneath. It costs nothing at the table and strands nobody.
 *
 * ## What these percentages are, and are not
 *
 * An ordering, not a forecast. `SPREAD` in winProbability.ts is an anchoring
 * choice that has never been fitted against results, so the claim supported
 * here is "this board is better than that one", not "you will win 63% of the
 * time". Two guards, both cheap: whole percentage points only (see `pct`), and
 * the caveat said once, in the hint under the reading.
 *
 * Everything else on this screen exists to answer "so what do I do", and is
 * driven by the measured findings rather than by a single ranking number.
 */
export function Verdict({ board, onHighlight, dodgeMode = "onDemand" }: Props) {
  const scale = boardScale(board);
  const matrix: Matrix = useMemo(() => boardMatrix(board, scale), [board, scale]);
  const tau = evenThreshold(board.ourPlayers.length, scale.min, scale.max);
  // A perfect round, in points. `tau` still drives the verdict, but neither it
  // nor this is printed on its own -- they are the denominators the note lines
  // under each box read against, so the old totals stay legible without a
  // constant having to be parsed to make sense of them.
  const most = board.ourPlayers.length * scale.max;

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

  /*
    Who can they trap, and what did the board just cost us?

    Unconditional, like `reach` above and for the same reason: the exposed/safe
    split is reach's measured "a tied worst is forceable, a unique worst is not"
    rule, which is ten sorts of five numbers, not a search. The one solve here
    is `winChanceFloor` for `base`, and the panel already runs `outlook` -- two
    dozen sampled solves -- on every render, so one more is inside the noise.

    This exists because the old worst-matchup chip named a single cheap cell and
    went silent when a player picked up a SECOND bad matchup, which is exactly
    when protection gets hard. `protectionFocus` names the exposed players
    instead, and carries the round-win chance so a worsening board is visible
    rather than silent -- the delta a captain driving the app could not see.
  */
  const protect = useMemo(
    () => protectionFocus(matrix, scale.min, scale.max, board.ourTeamFirst),
    [matrix, scale.min, scale.max, board.ourTeamFirst],
  );

  /*
    The three headline numbers, in the currency that decides the round.

    `protect.base` is already the guaranteed figure: `winChanceFloor` and
    `protocolFloor` run the same minimax over the same protocol from the same
    side, and differ only in what they add up at the end. So the "Round odds"
    box that used to sit beside "Guaranteed" was the same reading twice, and
    the two are now one box. Checked rather than assumed -- Verdict.currency
    asserts the pair never disagree about who is ahead, on all 31 saved boards.

    The other two needed probability-valued twins:

      typical  the sampled-opponent read, solved in round-win chance rather
               than converted from a points answer afterwards. See
               `chanceOutlook` for why the conversion was rejected and what the
               honest version costs.
      ceiling  the best chance any remaining assignment can still reach, which
               is an enumeration rather than a Hungarian solve because P(>= 3)
               is not a sum. 0.24 ms; the cheapest number on the panel.
  */
  const chanceCeiling = useMemo(
    () => assignmentChanceExtremes(probabilityMatrix(matrix, scale.min, scale.max))[1],
    [matrix, scale.min, scale.max],
  );

  const chance = useMemo(
    () =>
      chanceOutlook(
        matrix,
        {
          ourPool: (1 << matrix.length) - 1,
          theirPool: (1 << matrix.length) - 1,
          attacker: -1,
          attackerSide: board.ourTeamFirst ? "our" : "their",
        },
        protect.base,
        scale.min,
        scale.max,
      ),
    [matrix, board.ourTeamFirst, protect.base, scale.min, scale.max],
  );

  /*
    `chance.expected` is a Monte Carlo mean over 24 sampled opponent boards, so
    comparing it to even money with a bare `>` hands the choice of advice to the
    random draw whenever the two are close.

    That is not hypothetical. In the points currency this screen used to read
    in, 5 of the 31 saved boards sat closer to the line than the observed
    sampling error and one sat exactly on it, so the app was confidently
    recommending "play for the win" or "you need them to give you something" --
    opposite instructions -- on a coin flip.

    Two standard errors is the band, checked rather than assumed: against a
    4000-trial reference the true error fell inside 2 stderr on 29 of 31 boards
    and never exceeded it. The reply is to say so, because "too close to call"
    is a real answer and the wrong half of a confident answer is not.

    Worth recording that the move to round-win chance made this rarer rather
    than commoner: no saved board now lands inside its own band, where one did
    in points. That is not the guard becoming decorative, it is the currency
    separating boards that a total could not tell apart -- and it is why
    Verdict.tooclose has to construct a board on the line to test it.
  */
  const tooCloseToCall = Math.abs(chance.expected - 0.5) < 2 * chance.stderr;

  const exposedSet = new Set(protect.exposed.map((p) => p.ours));
  // The sharp version of the shared-column trap: one of their nominations that
  // pressures two players who are BOTH already forceable, so there is no line
  // that keeps both clear. A column that merely dips several players below the
  // midpoint is common and near-silent; this is the one that forces a choice.
  const sharedTrap =
    protect.joint
      .map((j) => ({ j, exposed: j.ours.filter((o) => exposedSet.has(o)).length }))
      .filter((x) => x.exposed >= 2)
      .sort((a, b) => b.exposed - a.exposed || a.j.worst - b.j.worst || a.j.theirs - b.j.theirs)[0]
      ?.j ?? null;
  const focusLevel =
    protect.focus === null ? 0 : protect.players[protect.focus].forcedLevel;
  const exposedCells = new Set(
    protect.exposed.flatMap((p) =>
      matrix[p.ours].flatMap((v, theirs) => (v === p.rowWorst ? [`${p.ours}-${theirs}`] : [])),
    ),
  );

  // A protocol-shielded player whose forced floor is still below the midpoint is
  // shieldable, not safe: refusing their lone worst only concedes the next-worst.
  // Splitting here keeps the "protecting them buys nothing" message off a player
  // the captain still has to sequence around.
  const trulySafe = shielded.filter((f) => f.level >= protect.mid);
  const shieldableFloors = shielded.filter((f) => f.level < protect.mid);
  const shieldableCells = new Set(
    shieldableFloors.flatMap((f) =>
      matrix[f.ours].flatMap((v, theirs) =>
        v === f.rowWorst || v === f.level ? [`${f.ours}-${theirs}`] : [],
      ),
    ),
  );

  // Rosters are frequently half-typed, so a blank name has to degrade into
  // something you can still find on the grid rather than an empty gap in a
  // sentence.
  const ourName = (i: number) => board.ourPlayers[i]?.trim() || `Your player ${i + 1}`;
  const theirName = (i: number) => board.theirPlayers[i]?.trim() || `Their list ${i + 1}`;

  // A single matchup's rating, read as the chance our player wins that one game.
  // The prose speaks the grid's own unit (#82): a bare "2" means nothing without
  // the scale, which is a dropdown three sections down; "about 25% a game" does
  // not. Same mapping the solver reasons in, and scale-independent.
  const winPct = (rating: number) => pct(toWinProbability(rating, scale.min, scale.max));

  // Who leads the protect-first decision, and whether it is even a decision the
  // engine can make: a 2+ tie means the free fields rank them equal, so the
  // honest thing is to hand the choice back rather than name one.
  const priorityNames = listNames(protect.priorityTie.map((o) => ourName(o)));
  const priorityTied = protect.priorityTie.length >= 2;

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
          value={pct(protect.base)}
          note={`${fmt(guaranteed)} of ${fmt(most)} if they hunt you perfectly`}
          strong
        />
        <Stat
          label="Typical"
          value={pct(chance.expected)}
          note={`${fmt(typical.expected)} of ${fmt(most)} if they play their own board`}
          strong
        />
        <Stat
          label="Ceiling"
          value={pct(chanceCeiling)}
          note={`${fmt(o.ceiling)} of ${fmt(most)} best still reachable`}
        />
      </div>

      <p className="reading">
        {o.verdict === UNWINNABLE ? (
          <>
            Every remaining pairing loses this round. The best still reachable is{" "}
            {pct(chanceCeiling)}, and a round is won by being better than even. Play for
            the points you can still bank, not for the win.
          </>
        ) : o.verdict === SECURED ? (
          <>
            The round is already won, whatever they do next -- every pairing left on the
            board is the right side of a coin flip. Anything further is bonus.
          </>
        ) : protect.base > 0.5 ? (
          <>
            Playing this out properly guarantees {pct(protect.base)} of taking the round,
            and that cannot be taken away from you.
          </>
        ) : tooCloseToCall ? (
          <>
            The safe reading is {pct(protect.base)}. Playing their own board they leave you
            around {pct(chance.expected)}, which is on the line rather than over it. This
            one is genuinely too close to call: the typical case and a coin flip are the
            same number to within the accuracy of the estimate, so treat it as one, and as
            a board the ceiling at {pct(chanceCeiling)} can still win for you.
          </>
        ) : chance.expected > 0.5 ? (
          <>
            The safe reading is {pct(protect.base)}, but that credits them with knowing
            exactly which matchups hurt you most. Playing their own board they leave you
            nearer {pct(chance.expected)}, which is the right side of the flip. This is a
            round you take by playing for the win, not by protecting the floor.
          </>
        ) : (
          <>
            Guaranteed {pct(protect.base)}, typically {pct(chance.expected)} -- both the
            wrong side of a coin flip. The win has to come from the ceiling at{" "}
            {pct(chanceCeiling)}, so it needs them to give you something.
          </>
        )}
      </p>

      {/*
        Said once, where the numbers are, and not repeated beside each of them.
        The percentages rank options honestly and forecast nothing, and a reader
        who does not know that will over-trust them.
      */}
      <p className="hint">
        Percentages are the chance of winning three of the five games, from a fixed
        rating-to-probability slope that has never been fitted against results. Read them
        as an ordering between options, not as a forecast for this round.
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
                ? `Worth about ${winPct(worstDodge.rating)} a game, and no line of play escapes it -- they can force
                   it whatever you do. Plan the other four around eating this one rather than
                   spending decisions trying to dodge what cannot be dodged.`
                : worstDodge.cheapest.free
                  ? `${board.ourPlayers[worstDodge.cheapest.cell.ours]} into
                     ${board.theirPlayers[worstDodge.cheapest.cell.theirs]} is worth about
                     ${winPct(worstDodge.rating)} a game, and refusing it costs nothing measurable -- your
                     chance of taking the round is the same either way. Take the dodge.`
                  : `${board.ourPlayers[worstDodge.cheapest.cell.ours]} into
                     ${board.theirPlayers[worstDodge.cheapest.cell.theirs]} is worth about
                     ${winPct(worstDodge.rating)} a game. Staying out of it drops your chance of taking the
                     round from ${pct(worstDodge.cheapest.base)} to
                     ${pct(worstDodge.cheapest.avoided ?? 0)}. That is the price of the dodge --
                     worth paying only if you think that number understates how bad it is.`
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

        {protect.exposed.length > 0 && (
          <Insight
            title={
              protect.exposed.length === 1
                ? `${ourName(protect.exposed[0].ours)} can be forced into their worst matchup`
                : `${listNames(protect.exposed.map((p) => ourName(p.ours)))} can be forced into their worst matchups`
            }
            body={
              protect.exposed.length === 1
                ? `A matchup worth about ${winPct(protect.exposed[0].rowWorst)} a game is repeated in their row
                   (${protect.exposed[0].floorCount} of them), and a repeated worst cell cannot be
                   refused -- the opponent picks the moment to spring it. You cannot dodge them
                   clear, so do not spend nominations trying: sequence so the hit lands in the
                   least bad of those cells, and protect where refusing actually works. The
                   guaranteed chance above falls as this gets worse.`
                : `Each has a repeated worst cell, and a repeated worst cannot be refused -- one
                   nomination is enough to spring it. ${
                     priorityTied
                       ? `${priorityNames} are equally exposed at about ${winPct(focusLevel)} a game -- same forced floor,
                   same number of ways to force it -- so there is no protect-first here: decide which
                   one eats it before the opponent decides for you.`
                       : `${ourName(protect.focus ?? protect.exposed[0].ours)}
                   is the deepest at about ${winPct(focusLevel)} a game, so weigh sequencing around them first.`
                   } Protecting all of them is not on the table; aim each into the least bad of
                   their tied cells. The guaranteed chance above falls as any of these deepen.`
            }
            onFocus={() => onHighlight?.(exposedCells)}
          />
        )}

        {sharedTrap && (
          <Insight
            title={`${theirName(sharedTrap.theirs)} squeezes ${listNames(
              sharedTrap.ours.filter((o) => exposedSet.has(o)).map((o) => ourName(o)),
            )} at once`}
            body={`Both are below the midpoint against them and both have a repeated worst cell,
              so a single nomination pressures two players you already cannot fully protect.
              There is no line that keeps both clear -- decide now which one eats it rather than
              discovering the choice was made for you.`}
            onFocus={() =>
              onHighlight?.(
                new Set(
                  sharedTrap.ours
                    .filter((o) => exposedSet.has(o))
                    .map((o) => `${o}-${sharedTrap.theirs}`),
                ),
              )
            }
          />
        )}

        {shieldableFloors.length > 0 && (
          <Insight
            title={
              shieldableFloors.length === 1
                ? `${ourName(shieldableFloors[0].ours)} can be shielded from their worst, but not into a good matchup`
                : `${listNames(shieldableFloors.map((f) => ourName(f.ours)))} can be shielded from their worst, but not into a good matchup`
            }
            body={
              shieldableFloors.length === 1
                ? `Their worst cell is a lone matchup worth about ${winPct(shieldableFloors[0].rowWorst)} a
                   game, so it can be refused -- but the next matchup they can be forced into is only
                   about ${winPct(shieldableFloors[0].level)} a game, still below the midpoint. You keep
                   ${ourName(shieldableFloors[0].ours)} out of that about-${winPct(shieldableFloors[0].rowWorst)}
                   game only by conceding the about-${winPct(shieldableFloors[0].level)} one, so a nomination here buys
                   the smaller hit, not safety. Sequence them ahead of the players who are genuinely
                   fine.`
                : `Each has a lone worst cell that can be refused, but the next cell they can be
                   forced into is still below the midpoint. Refusing the worst only concedes the
                   next-worst, so they are protectable, not safe -- weigh them after the exposed
                   players and ahead of the genuinely fine ones.`
            }
            onFocus={() => onHighlight?.(shieldableCells)}
          />
        )}

        {trulySafe.length > 0 && (
          <Insight
            title={
              trulySafe.length === 1
                ? `${ourName(trulySafe[0].ours)} cannot be forced into their worst matchup`
                : `${listNames(trulySafe.map((f) => ourName(f.ours)))} cannot be forced into their worst matchups`
            }
            body={
              trulySafe.length === 1
                ? `Their worst cell is worth about ${winPct(trulySafe[0].rowWorst)} a game and it is the
                   only matchup that low in that row -- a single cell, and a single cell can always be
                   refused. The worst they can actually be held to is about ${winPct(trulySafe[0].level)}
                   a game. Spending a nomination to protect them buys nothing.`
                : `Each of their worst cells is the only one of its rating in that row, and a
                   lone matchup can always be refused. Their real floors are better than the
                   grid reads. Spend nominations on the players whose bad matchup is repeated
                   -- those are the ones that can genuinely be forced.`
            }
            onFocus={() =>
              onHighlight?.(
                new Set(trulySafe.flatMap((f) => f.via.map((t) => `${f.ours}-${t}`))),
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
                ? `Your best cell against them is worth about ${winPct(overstated[0].columnBest)} a game, but
                   it is the only cell that good in that column, so they can refuse it
                   and you cannot insist. ${overstated[0].level === null ? "" : `Settle for about ${winPct(overstated[0].level)} a game instead.`}
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
