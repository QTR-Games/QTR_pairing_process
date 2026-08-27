import { useMemo } from "react";
import { winChanceFloor } from "../../engine/avoidance";
import type { Matrix } from "../../engine/boardAnalysis";
import { protocolFloor } from "../../engine/protocol";
import type { Board } from "../../model/board";
import { pct } from "../../model/format";
import type { Scale } from "../../model/scale";

interface Props {
  board: Board;
  scale: Scale;
  matrix: Matrix;
  tau: number;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

/**
 * The two currencies, side by side, instead of one of them.
 *
 * The app has always had both and has always had to pick one per screen,
 * because two four-number blocks do not fit above the fold on a phone. They
 * measure different things and the difference is the interesting part:
 *
 *  - Points are what the tournament records. A round total is compared against
 *    the threshold and that is the result.
 *  - Probability is what actually decides it. Five games get played and three
 *    of them have to fall your way; `winProbability.ts` turns the same ratings
 *    into P(win at least three).
 *
 * They can disagree, because a points total is nearly indifferent to *which*
 * cells make it up while a win probability is not. Two boards totalling the
 * same can sit either side of a coin flip, and when that happens the points
 * reading is the one that is lying to you.
 *
 * The probability figure carries a real caveat and it is printed on screen
 * rather than buried: `SPREAD` in winProbability.ts is an anchoring choice, not
 * a measured quantity. Read the percentages as an ordering between boards, not
 * as a forecast for this one.
 */
export function Currencies({ board, scale, matrix, tau }: Props) {
  const ptsWe = useMemo(() => protocolFloor(matrix, true).value, [matrix]);
  const ptsThey = useMemo(() => protocolFloor(matrix, false).value, [matrix]);

  const chanceWe = useMemo(
    () => winChanceFloor(matrix, scale.min, scale.max, true),
    [matrix, scale.min, scale.max],
  );
  const chanceThey = useMemo(
    () => winChanceFloor(matrix, scale.min, scale.max, false),
    [matrix, scale.min, scale.max],
  );

  const pts = board.ourTeamFirst ? ptsWe : ptsThey;
  const chance = board.ourTeamFirst ? chanceWe : chanceThey;

  const pointsSaysWin = pts > tau + 1e-9;
  const chanceSaysWin = chance > 0.5;
  const disagree = pointsSaysWin !== chanceSaysWin;

  // Which side to take on the dice-off, in each currency independently. Across
  // the 31 saved boards these agreed 31/31, which is worth knowing but is not
  // a law -- so both are computed rather than one being assumed.
  const ptsGain = Math.abs(ptsWe - ptsThey);
  const ptsPrefersOpen = ptsWe > ptsThey;
  const chanceGain = Math.abs(chanceWe - chanceThey);
  const chancePrefersOpen = chanceWe > chanceThey;
  const diceAgree = ptsGain < 0.005 || chanceGain < 0.0005 || ptsPrefersOpen === chancePrefersOpen;

  return (
    <section className="panel currencies">
      <h2>Both currencies</h2>

      <div className="cur-grid">
        <div className="cur-col">
          <h3 className="panel-sub">Points</h3>
          <p className="cur-big">{fmt(pts)}</p>
          <p className="hint">guaranteed total, threshold {fmt(tau)}</p>
          <p className={"cur-verdict " + (pointsSaysWin ? "win" : "loss")}>
            {pointsSaysWin ? "Above the line" : "Not above the line"}
          </p>
          <dl className="cur-rows">
            <div>
              <dt>We nominate first</dt>
              <dd>{fmt(ptsWe)}</dd>
            </div>
            <div>
              <dt>They nominate first</dt>
              <dd>{fmt(ptsThey)}</dd>
            </div>
          </dl>
        </div>

        <div className="cur-col">
          <h3 className="panel-sub">Round win chance</h3>
          <p className="cur-big">{pct(chance)}</p>
          <p className="hint">P(win 3 of 5), same adversarial search</p>
          <p className={"cur-verdict " + (chanceSaysWin ? "win" : "loss")}>
            {chanceSaysWin ? "Favourite" : "Underdog"}
          </p>
          <dl className="cur-rows">
            <div>
              <dt>We nominate first</dt>
              <dd>{pct(chanceWe)}</dd>
            </div>
            <div>
              <dt>They nominate first</dt>
              <dd>{pct(chanceThey)}</dd>
            </div>
          </dl>
        </div>
      </div>

      {disagree && (
        <p className="insight warn-row">
          <strong>The two disagree.</strong> Points put you{" "}
          {pointsSaysWin ? "above" : "below"} the threshold while the games put you{" "}
          {chanceSaysWin ? "ahead" : "behind"} at {pct(chance)}. A total is nearly
          indifferent to which cells make it up; three wins out of five is not.
        </p>
      )}

      <p className="insight">
        <strong>Dice-off.</strong>{" "}
        {ptsGain < 0.005 && chanceGain < 0.0005 ? (
          <>It does not matter here -- both sides of the roll price out level.</>
        ) : (
          <>
            Points want you to {ptsPrefersOpen ? "nominate first" : "make them nominate first"} by{" "}
            {fmt(ptsGain)}; the games want you to{" "}
            {chancePrefersOpen ? "nominate first" : "make them nominate first"} by{" "}
            {pct(chanceGain)}.{" "}
            {diceAgree
              ? "They agree."
              : "They disagree -- rare, and worth a second look at the board."}
          </>
        )}
      </p>

      <p className="hint">
        Percentages come from a fixed rating-to-probability slope that has never
        been fitted against results. Treat them as an ordering between boards,
        not as a forecast for this one.
      </p>
    </section>
  );
}
